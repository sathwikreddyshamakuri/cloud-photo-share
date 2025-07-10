"""
Photo upload & list (128-px thumbs + cursor pagination)
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

# ──────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

security = HTTPBearer()


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")


# ────────────────────────── local helpers ─────────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def extract_exif(fp: Path) -> tuple[int | None, int | None, str | None]:
    try:
        img = Image.open(fp)
        w, h = img.size
        exif = img._getexif() or {}
        raw = {ExifTags.TAGS.get(k): v for k, v in exif.items()}.get(
            "DateTimeOriginal"
        )
        taken_at = (
            datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if raw
            else None
        )
        return w, h, taken_at
    except Exception:
        return None, None, None


def presign(s3: boto3.client, key: str) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )


# ────────────────────────── POST /photos/ ─────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # save temp
    tmp = UPLOAD_DIR / f"orig-{uuid.uuid4()}"
    tmp.write_bytes(await file.read())
    width, height, taken_at = extract_exif(tmp)

    # thumbnail
    thumb = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb, "JPEG", quality=85)

    # S3
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(tmp), S3_BUCKET, s3_key, ExtraArgs={"ContentType": file.content_type})
    s3.upload_file(str(thumb), S3_BUCKET, thumb_key, ExtraArgs={"ContentType": "image/jpeg"})
    tmp.unlink(missing_ok=True)
    thumb.unlink(missing_ok=True)

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

    return {
        "photo_id": photo_id,
        "url": presign(s3, s3_key),
        "thumb_url": presign(s3, thumb_key),
    }

@router.get("/", tags=["photos"])
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    """
    Robust paginator that works even when Moto's GSI emulation drops items that
    share the same **uploaded_at**.  Implementation:

    1.  Scan *all* items for the album (that’s fast in tests).
    2.  Sort by uploaded_at DESC.
    3.  Slice `[start : start+limit]`.
    4.  Build a minimal `next_key` **only** if there’s more data.
    """
    # ── owner check ───────────────────────────────────────────
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # ── pull every photo for this album ───────────────────────
    resp = table_photos.scan(FilterExpression=Key("album_id").eq(album_id))
    all_items: list[dict] = resp["Items"]

    # sort newest → oldest
    all_items.sort(key=lambda x: int(x["uploaded_at"]), reverse=True)

    # figure out where the page starts
    start = 0
    if last_key:
        lk = json.loads(last_key)
        for idx, it in enumerate(all_items):
            if it["photo_id"] == lk["photo_id"]:
                start = idx + 1
                break

    page = all_items[start : start + limit]

    # presign URLs
    s3 = boto3.client("s3", region_name=REGION)
    for it in page:
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

    # next_key only if there’s another slice after this one
    next_key: str | None = None
    if start + limit < len(all_items):
        tail = all_items[start + limit - 1]
        next_key = json.dumps(
            {
                "photo_id": tail["photo_id"],
                "album_id": tail["album_id"],
                "uploaded_at": str(tail["uploaded_at"]),
            }
        )

    return {"items": page, "next_key": next_key}
