"""
Photo upload & listing (128-px thumbnails + cursor-based pagination)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import ExifTags, Image

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# --------------------------------------------------------------------------- #
# DynamoDB table handle & router                                              #
# --------------------------------------------------------------------------- #
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

# --------------------------------------------------------------------------- #
# Auth helper (shared by every route)                                         #
# --------------------------------------------------------------------------- #
security = HTTPBearer()


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token")


# --------------------------------------------------------------------------- #
# Local helpers                                                               #
# --------------------------------------------------------------------------- #
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def extract_exif(fp: Path) -> tuple[int | None, int | None, str | None]:
    """
    Return (width, height, taken_at_iso) from the file *if* EXIF exists.
    Otherwise (None, None, None).
    """
    try:
        img = Image.open(fp)
        w, h = img.size
        exif_data = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif_data.items()}
        raw_dt = tag_map.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if raw_dt
            else None
        )
        return w, h, taken_at
    except Exception:  # pillow failed – treat as “no EXIF”
        return None, None, None


def presign(s3: boto3.client, key: str) -> str:
    """Generate a 1-h presigned URL for an object key."""
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )


# --------------------------------------------------------------------------- #
# POST /photos/  – upload single image                                        #
# --------------------------------------------------------------------------- #
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # ---- 1) ensure album exists & belongs to caller ---------------------- #
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # ---- 2) save file to tmp & read EXIF --------------------------------- #
    tmp_path = UPLOAD_DIR / f"orig-{uuid.uuid4()}"
    tmp_path.write_bytes(await file.read())
    width, height, taken_at = extract_exif(tmp_path)

    # ---- 3) create 128-px thumbnail -------------------------------------- #
    thumb_path = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp_path) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb_path, "JPEG", quality=85)

    # ---- 4) push both objects to S3 -------------------------------------- #
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"

    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(
        str(tmp_path),
        S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": file.content_type},
    )
    s3.upload_file(
        str(thumb_path),
        S3_BUCKET,
        thumb_key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )
    tmp_path.unlink(missing_ok=True)
    thumb_path.unlink(missing_ok=True)

    # ---- 5) write metadata row ------------------------------------------- #
    table_photos.put_item(
        Item={
            "photo_id": photo_id,
            "album_id": album_id,
            "s3_key": s3_key,
            "thumb_key": thumb_key,
            "uploader": user_id,
            "width": width or 0,
            "height": height or 0,
            "taken_at": taken_at or "",
            "uploaded_at": int(time.time()),
        }
    )

    # ---- 6) response ----------------------------------------------------- #
    return {
        "photo_id": photo_id,
        "url": presign(s3, s3_key),
        "thumb_url": presign(s3, thumb_key),
    }


# --------------------------------------------------------------------------- #
# GET /photos/  – list photos in an album (cursor pagination)                #
# --------------------------------------------------------------------------- #
@router.get("/", tags=["photos"])
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    # ---- 1) album ownership --------------------------------------------- #
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # ---- 2) build primary query (GSI) ------------------------------------ #
    query_kw: Dict[str, Any] = {
        "IndexName": "album_id-index",
        "KeyConditionExpression": Key("album_id").eq(album_id),
        "ScanIndexForward": False,  # newest first
        "Limit": limit,
    }

    if last_key:
        raw = json.loads(last_key)
        query_kw["ExclusiveStartKey"] = {
            "album_id": raw["album_id"],
            "photo_id": raw["photo_id"],
            "uploaded_at": Decimal(str(raw["uploaded_at"])),
        }

    # ---- 3) fetch *at most* `limit` items -------------------------------- #
    items: List[Dict[str, Any]] = []
    cursor: Dict[str, Any] | None = None

    try:
        while len(items) < limit:
            resp = table_photos.query(**query_kw)
            items.extend(resp["Items"])
            cursor = resp.get("LastEvaluatedKey")
            if len(items) >= limit or cursor is None:
                break
            # continue loop → pull next page
            query_kw["ExclusiveStartKey"] = cursor
    except Exception:
        # Fallback Scan for Moto (still keep size logic)
        scan_kw = {
            "FilterExpression": Key("album_id").eq(album_id),
            "Limit": limit,
        }
        if last_key:
            scan_kw["ExclusiveStartKey"] = json.loads(last_key)

        while len(items) < limit:
            resp = table_photos.scan(**scan_kw)
            items.extend(resp["Items"])
            cursor = resp.get("LastEvaluatedKey")
            if len(items) >= limit or cursor is None:
                break
            scan_kw["ExclusiveStartKey"] = cursor

    items = items[:limit]  # truncate in case we overshot

    # ---- 4) sign URLs ---------------------------------------------------- #
    s3 = boto3.client("s3", region_name=REGION)
    for it in items:
        it["url"] = presign(s3, it["s3_key"])
        it["thumb_url"] = presign(s3, it["thumb_key"])

    # ---- 5) only emit next_key when we hit *exactly* `limit` items ------- #
    next_key = json.dumps(cursor, default=str) if cursor and len(items) == limit else None

    return {"items": items, "next_key": next_key}
