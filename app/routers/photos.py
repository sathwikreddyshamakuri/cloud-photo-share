"""
Photo upload & listing (with 128-px thumbnails and DynamoDB pagination)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image, ExifTags

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# ────────────────────────────────
# Router / tables / auth helper
# ────────────────────────────────
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

security = HTTPBearer()


def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """JWT → user_id or 401."""
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token") from None


# ────────────────────────────────
# Local helpers
# ────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def extract_exif(fp: Path) -> tuple[int | None, int | None, str | None]:
    try:
        img = Image.open(fp)
        w, h = img.size
        exif = img._getexif() or {}
        raw_dt = {ExifTags.TAGS.get(k): v for k, v in exif.items()}.get(
            "DateTimeOriginal"
        )
        taken_at = (
            datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if raw_dt
            else None
        )
        return w, h, taken_at
    except Exception:
        return None, None, None


# ────────────────────────────────
# POST /photos/ (upload)
# ────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # 1. Album ownership
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # 2. Save temp file
    tmp = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp.open("wb") as out:
        out.write(await file.read())

    width, height, taken_at = extract_exif(tmp)

    # 3. Build thumbnail
    thumb = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb, "JPEG", quality=85)

    # 4. Upload both to S3
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"

    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(tmp), S3_BUCKET, s3_key, ExtraArgs={"ContentType": file.content_type})
    s3.upload_file(str(thumb), S3_BUCKET, thumb_key, ExtraArgs={"ContentType": "image/jpeg"})
    tmp.unlink(missing_ok=True)
    thumb.unlink(missing_ok=True)

    # 5. Metadata in DynamoDB
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

    # 6. Response
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600
    )
    thumb_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": thumb_key}, ExpiresIn=3600
    )
    return {"photo_id": photo_id, "url": url, "thumb_url": thumb_url}


# ────────────────────────────────
# GET /photos/ (paginated list)
# ────────────────────────────────
@router.get("/")
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    # 1. Album ownership
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # 2. Try GSI query first
    query_kw: dict[str, Any] = {
        "IndexName": "album_id-index",
        "KeyConditionExpression": Key("album_id").eq(album_id),
        "ScanIndexForward": False,  # newest first
        "Limit": limit,
    }
    if last_key:
        lk = json.loads(last_key)
        query_kw["ExclusiveStartKey"] = {
            "album_id": lk["album_id"],
            "uploaded_at": Decimal(str(lk["uploaded_at"])),
            "photo_id": lk["photo_id"],
        }

    try:
        resp = table_photos.query(**query_kw)
    except Exception:
        # Local/Moto fallback – Scan
        scan_kw: dict[str, Any] = {
            "FilterExpression": Key("album_id").eq(album_id),
            "Limit": limit,
        }
        if last_key:
            scan_kw["ExclusiveStartKey"] = json.loads(last_key)
        resp = table_photos.scan(**scan_kw)

    items = resp["Items"]

    # 3. Remove duplicate “first row” (same ts) that GSI can emit
    if last_key:
        prev = json.loads(last_key)
        dup_ts = Decimal(str(prev["uploaded_at"]))
        dup_pid = prev["photo_id"]

        def is_dup(it: dict[str, Any]) -> bool:
            ts = Decimal(str(it.get("uploaded_at", "0")))
            return ts == dup_ts and it.get("photo_id") <= dup_pid

        items = [it for it in items if not is_dup(it)]

    # 4. Presign URLs
    s3 = boto3.client("s3", region_name=REGION)
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )
        it["thumb_url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["thumb_key"]},
            ExpiresIn=3600,
        )

    # 5. Next-page token only if we truly have more
    if len(items) == limit and "LastEvaluatedKey" in resp:
        next_key = json.dumps(resp["LastEvaluatedKey"], default=str)
    else:
        next_key = None

    return {"items": items, "next_key": next_key}
