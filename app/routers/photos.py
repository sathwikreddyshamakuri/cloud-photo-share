"""
Photo upload + list (with 128-px thumbnails & pagination)
"""

import os, time, uuid, json
from pathlib import Path
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import (
    APIRouter, UploadFile, File,
    HTTPException, Depends, status
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image, ExifTags

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# ── router & table ───────────────────────────────────────────
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

# ── auth helper ──────────────────────────────────────────────
security = HTTPBearer()
def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")

# ── temp dir & EXIF helper ───────────────────────────────────
UPLOAD_DIR = Path("uploads"); UPLOAD_DIR.mkdir(exist_ok=True)

def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        w, h = img.size
        exif = img._getexif() or {}
        raw  = {ExifTags.TAGS.get(k): v for k, v in exif.items()}.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc).isoformat()
        ) if raw else None
        return w, h, taken_at
    except Exception:
        return None, None, None

# ── POST /photos/ ────────────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # ownership
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # save temp
    tmp = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp.open("wb") as out:
        out.write(await file.read())
    width, height, taken_at = extract_exif(tmp)

    # thumbnail
    thumb = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb, "JPEG", quality=85)

    # S3 upload
    photo_id  = str(uuid.uuid4())
    s3_key    = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(tmp),   S3_BUCKET, s3_key,
                   ExtraArgs={"ContentType": file.content_type})
    s3.upload_file(str(thumb), S3_BUCKET, thumb_key,
                   ExtraArgs={"ContentType": "image/jpeg"})
    tmp.unlink(missing_ok=True); thumb.unlink(missing_ok=True)

    # Dynamo
    table_photos.put_item(Item={
        "photo_id":   photo_id,
        "album_id":   album_id,
        "s3_key":     s3_key,
        "thumb_key":  thumb_key,
        "uploader":   user_id,
        "width":      width or 0,
        "height":     height or 0,
        "taken_at":   taken_at or "",
        "uploaded_at": int(time.time()),
    })

    url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600)
    thumb_url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": thumb_key}, ExpiresIn=3600)
    return {"photo_id": photo_id, "url": url, "thumb_url": thumb_url}

# ── GET /photos/ ─────────────────────────────────────────────
@router.get("/", tags=["photos"])
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    # ownership check
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    used_gsi = True
    try:
        from decimal import Decimal
        query_kw = {
            "IndexName": "album_id-index",
            "KeyConditionExpression": Key("album_id").eq(album_id),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if last_key:
            raw = json.loads(last_key)
            query_kw["ExclusiveStartKey"] = {
                "album_id":   raw["album_id"],
                "uploaded_at": Decimal(str(raw["uploaded_at"])),
            }
        resp = table_photos.query(**query_kw)
    except Exception:
        used_gsi = False   # fallback to scan
        resp = table_photos.scan(
            FilterExpression=Key("album_id").eq(album_id),
            Limit=limit,
        )

    items = resp["Items"]

    # presign URLs
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

    next_key = (
        json.dumps(resp["LastEvaluatedKey"], default=str)
        if used_gsi and "LastEvaluatedKey" in resp else None
    )
    return {"items": items, "next_key": next_key}
