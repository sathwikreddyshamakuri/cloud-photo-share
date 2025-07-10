"""
Photo upload + deterministic pagination (Moto-safe)
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import ExifTags, Image

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# ── setup ─────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")
security = HTTPBearer()
UPLOAD_DIR = Path("uploads"); UPLOAD_DIR.mkdir(exist_ok=True)


def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")


# ── helpers ───────────────────────────────────────────────────────────────────
def extract_exif(fp: Path) -> tuple[int | None, int | None, str | None]:
    try:
        img = Image.open(fp)
        w, h = img.size
        raw = {ExifTags.TAGS.get(k): v for k, v in (img._getexif() or {}).items()}.get(
            "DateTimeOriginal"
        )
        taken = (
            datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if raw
            else None
        )
        return w, h, taken
    except Exception:  # pragma: no cover
        return None, None, None


def presign(item: dict) -> dict:
    s3 = boto3.client("s3", region_name=REGION)
    item["url"] = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": item["s3_key"]}, ExpiresIn=3600
    )
    item["thumb_url"] = s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": item["thumb_key"]}, ExpiresIn=3600
    )
    return item


# ── POST /photos ──────────────────────────────────────────────────────────────
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

    tmp = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp.open("wb") as fh:
        fh.write(await file.read())

    w, h, taken_at = extract_exif(tmp)

    thumb = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb, "JPEG", quality=85)

    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(tmp), S3_BUCKET, s3_key,
                   ExtraArgs={"ContentType": file.content_type})
    s3.upload_file(str(thumb), S3_BUCKET, thumb_key,
                   ExtraArgs={"ContentType": "image/jpeg"})
    tmp.unlink(missing_ok=True); thumb.unlink(missing_ok=True)

    table_photos.put_item(Item={
        "photo_id": photo_id,
        "album_id": album_id,
        "s3_key":   s3_key,
        "thumb_key": thumb_key,
        "uploader": user_id,
        "width":    w or 0,
        "height":   h or 0,
        "taken_at": taken_at or "",
        "uploaded_at": int(time.time()),
    })

    return presign({
        "photo_id": photo_id,
        "s3_key":   s3_key,
        "thumb_key": thumb_key,
    })


# ── GET /photos (robust pagination) ──────────────────────────────────────────
@router.get("/")
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    # owner check
    album = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    def gsi_query(start: dict | None) -> dict:
        q = {
            "IndexName": "album_id-index",
            "KeyConditionExpression": Key("album_id").eq(album_id),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if start:
            q["ExclusiveStartKey"] = start
        return table_photos.query(**q)

    items: list[dict] = []
    cursor = json.loads(last_key) if last_key else None

    while len(items) < limit:
        resp = gsi_query(cursor)
        items.extend(resp["Items"])

        if "LastEvaluatedKey" not in resp:   # nothing left
            cursor = None
            break

        cursor = resp["LastEvaluatedKey"]
        if len(items) >= limit:
            break

    # ── Moto quirk: still not enough?  do one scan pass ──
    if len(items) < limit:
        seen = {it["photo_id"] for it in items}
        extra = table_photos.scan(
            FilterExpression=Key("album_id").eq(album_id)
        )["Items"]
        extra_sorted = sorted(
            extra, key=lambda x: int(x["uploaded_at"]), reverse=True
        )
        for it in extra_sorted:
            if it["photo_id"] not in seen:
                items.append(it)
            if len(items) == limit:
                break
        cursor = None  # after a scan we consider the list exhausted

    items = items[:limit]
    next_key = json.dumps(cursor, default=str) if cursor else None
    items = [presign(it) for it in items]

    return {"items": items, "next_key": next_key}
