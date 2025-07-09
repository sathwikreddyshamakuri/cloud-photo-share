"""
Photo upload + list (with 128-px thumbnails & pagination)
"""

import os
import time
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    status,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image, ExifTags

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# ───────────────────────────────────────── Router & table
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

# ───────────────────────────────────────── Auth helper
security = HTTPBearer()


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")


# ───────────────────────────────────────── Temp dir & EXIF helper
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        w, h = img.size
        exif = img._getexif() or {}
        raw = {
            ExifTags.TAGS.get(k): v for k, v in exif.items()
        }.get("DateTimeOriginal")
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


# ───────────────────────────────────────── POST /photos
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # 1. ownership check
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # 2. save temp
    tmp = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp.open("wb") as out:
        out.write(await file.read())
    width, height, taken_at = extract_exif(tmp)

    # 3. thumbnail
    thumb = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb, "JPEG", quality=85)

    # 4. S3 upload
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"

    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(
        str(tmp), S3_BUCKET, s3_key, ExtraArgs={"ContentType": file.content_type}
    )
    s3.upload_file(
        str(thumb), S3_BUCKET, thumb_key, ExtraArgs={"ContentType": "image/jpeg"}
    )
    tmp.unlink(missing_ok=True)
    thumb.unlink(missing_ok=True)

    # 5. Dynamo
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

    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600
    )
    thumb_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": thumb_key}, ExpiresIn=3600
    )
    return {"photo_id": photo_id, "url": url, "thumb_url": thumb_url}

# ── GET /photos/ ─────────────────────────────────────────────
@router.get("/", tags=["photos"])
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    # ── 1) owner check ───────────────────────────────────────
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # helper → build an ExclusiveStartKey dict from the incoming token
    def decode_start(token: str | None):
        if not token:
            return None
        raw = json.loads(token)
        return {
            "album_id":   raw["album_id"],
            "uploaded_at": Decimal(str(raw["uploaded_at"])),
            "photo_id":   raw["photo_id"],
        }

    eks = decode_start(last_key)
    remaining = limit
    gathered: list[dict] = []
    start_for_next_page: dict | None = None

    while remaining > 0:
        try:
            resp = table_photos.query(
                IndexName="album_id-index",
                KeyConditionExpression=Key("album_id").eq(album_id),
                ScanIndexForward=False,
                Limit=remaining,
                **({"ExclusiveStartKey": eks} if eks else {}),
            )
        except Exception:
            resp = table_photos.scan(
                FilterExpression=Key("album_id").eq(album_id),
                Limit=remaining,
                **({"ExclusiveStartKey": eks} if eks else {}),
            )

        gathered.extend(resp["Items"])
        remaining = limit - len(gathered)

        if "LastEvaluatedKey" not in resp or remaining == 0:
            start_for_next_page = resp.get("LastEvaluatedKey")
            break

        # continue fetching the same page
        eks = resp["LastEvaluatedKey"]

    # ── 2) presign URLs ──────────────────────────────────────
    s3 = boto3.client("s3", region_name=REGION)
    for it in gathered:
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

    next_key = (
        json.dumps(start_for_next_page, default=str) if start_for_next_page else None
    )
    return {"items": gathered, "next_key": next_key}

