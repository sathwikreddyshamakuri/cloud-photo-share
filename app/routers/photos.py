# app/routers/photos.py
from fastapi import (
    APIRouter, UploadFile, File, Form, Query, Body,
    HTTPException, Depends, status
)
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key
from PIL import Image, ExifTags
import time
import uuid
import boto3

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums  # reuse Albums table

router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")
UPLOAD_DIR = Path("uploads")   # temp folder for PIL
UPLOAD_DIR.mkdir(exist_ok=True)

def current_user(token: str = Depends(decode_token)) -> str:
    # decode_token should return the user_id; if it returns a jwt payload,
    # adapt this to extract the subject/user id.
    return token

def _s3():
    return boto3.client("s3", region_name=REGION)

def _assert_album_ownership(album_id: str, user_id: str):
    resp = table_albums.get_item(Key={"album_id": album_id})
    album = resp.get("Item")
    if not album or album.get("owner") != user_id:
        raise HTTPException(404, "Album not found")

def _safe_filename(name: str) -> str:
    name = (name or "").strip().replace("\r", "").replace("\n", "")
    return name or "download.bin"

def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        width, height = img.size
        exif = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif.items()}
        taken_raw = tag_map.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(taken_raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if taken_raw else ""
        )
        return width or 0, height or 0, taken_at
    except Exception:
        return 0, 0, ""



class PresignIn(BaseModel):
    album_id: Optional[str] = None
    albumId: Optional[str] = None
    filename: str
    mime: Optional[str] = None



@router.post("/", status_code=status.HTTP_201_CREATED)
def create_photo_presigned(
    body: PresignIn = Body(...),
    user_id: str = Depends(current_user),
):
    album_id = body.album_id or body.albumId
    if not album_id:
        raise HTTPException(422, "album_id is required")

    _assert_album_ownership(album_id, user_id)

    filename = _safe_filename(body.filename or "upload.bin")
    mime = body.mime or "application/octet-stream"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"

    photo_id = str(uuid.uuid4())
    # Keep your existing key layout
    key = f"photos/{album_id}/{photo_id}-{filename}"

    # Create metadata now so list can show the item immediately
    now = int(time.time())
    table_photos.put_item(Item={
        "photo_id":    photo_id,
        "album_id":    album_id,
        "s3_key":      key,
        "uploader":    user_id,
        "filename":    filename,
        "width":       0,
        "height":      0,
        "taken_at":    "",
        "uploaded_at": now,
    })

    # Presigned PUT for browser upload
    s3 = _s3()
    put_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": mime},
        ExpiresIn=900,
    )

    return {
        "ok": True,
        "mode": "presigned_put",
        "photo_id": photo_id,
        "album_id": album_id,
        "s3_key": key,
        "put_url": put_url,
        "finalize_required": False,
    }

# -------------------- Upload (B): multipart direct (optional) --------------------

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_photo_multipart(
    album_id: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    _assert_album_ownership(album_id, user_id)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # temp file for EXIF
    temp_path = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with temp_path.open("wb") as tmp:
        tmp.write(await file.read())

    width, height, taken_at = extract_exif(temp_path)

    # Upload to S3
    photo_id = str(uuid.uuid4())
    filename = _safe_filename(file.filename or "upload.bin")
    key = f"photos/{album_id}/{photo_id}-{filename}"
    s3 = _s3()
    s3.upload_file(
        str(temp_path), S3_BUCKET, key,
        ExtraArgs={"ContentType": file.content_type or "application/octet-stream"}
    )
    temp_path.unlink(missing_ok=True)

    # store metadata
    table_photos.put_item(Item={
        "photo_id":    photo_id,
        "album_id":    album_id,
        "s3_key":      key,
        "uploader":    user_id,
        "filename":    filename,
        "width":       width,
        "height":      height,
        "taken_at":    taken_at,
        "uploaded_at": int(time.time())
    })

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600
    )
    return {"ok": True, "mode": "multipart", "photo_id": photo_id, "url": url}



@router.get("/")
def list_photos(
    album_id: str = Query(...),
    limit: int = Query(50, gt=1),
    last_key: Optional[str] = Query(None),
    user_id: str = Depends(current_user),
):
    _assert_album_ownership(album_id, user_id)

    resp = table_photos.query(
        IndexName="album_id-index",
        KeyConditionExpression=Key("album_id").eq(album_id),
    )
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = table_photos.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(album_id),
            ExclusiveStartKey=resp["LastEvaluatedKey"],
        )
        items.extend(resp.get("Items", []))

    # sort by uploaded_at ascending
    items.sort(key=lambda p: p.get("uploaded_at", 0))

    # page window
    start = 0
    if last_key:
        for i, p in enumerate(items):
            if p.get("photo_id") == last_key:
                start = i + 1
                break
    page = items[start : start + limit]

    # attach URLs
    s3 = _s3()
    for p in page:
        key = p["s3_key"]
        fname = _safe_filename(p.get("filename") or key.split("/")[-1])
        p["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )
        p["download_url"] = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{fname}"',
            },
            ExpiresIn=3600,
        )

    next_key = page[-1]["photo_id"] if page and (start + limit) < len(items) else None
    return {"items": page, "next_key": next_key}



@router.delete("/{photo_id}/", status_code=204)
def delete_photo_trailing(photo_id: str, user_id: str = Depends(current_user)):
    return _delete_photo(photo_id, user_id)

@router.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: str, user_id: str = Depends(current_user)):
    return _delete_photo(photo_id, user_id)

def _delete_photo(photo_id: str, user_id: str):
    item = table_photos.get_item(Key={"photo_id": photo_id}).get("Item")
    if not item:
        raise HTTPException(404, "Photo not found")

    album_id = item["album_id"]
    _assert_album_ownership(album_id, user_id)

    table_photos.delete_item(Key={"photo_id": photo_id})
    try:
        _s3().delete_object(Bucket=S3_BUCKET, Key=item["s3_key"])
    except Exception:
        pass
    return {}
