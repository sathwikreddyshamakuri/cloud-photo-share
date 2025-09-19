# app/routers/photos.py
import uuid
import time
import os
from typing import Optional

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Query,
    Form,
    Body,
    HTTPException,
    Depends,
    status,
)
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")

MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))  # 25MB default



class PresignIn(BaseModel):
    # JSON body style for presigned flow
    album_id: Optional[str] = None
    albumId: Optional[str] = None
    filename: str
    mime: Optional[str] = None



def _assert_album_ownership(album_id: str, user_id: str):
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb.get("owner") != user_id:
        raise HTTPException(status_code=404, detail="Album not found")


def _safe_filename(name: str) -> str:
    # very light normalization for Content-Disposition
    name = (name or "").strip().replace("\r", "").replace("\n", "")
    return name or "download.bin"



@router.post("/photos/", status_code=status.HTTP_201_CREATED)
def create_photo_presigned(
    body: PresignIn = Body(...),
    user_id: str = Depends(current_user),
):
    album_id = body.album_id or body.albumId
    if not album_id:
        raise HTTPException(status_code=422, detail="album_id is required")

    _assert_album_ownership(album_id, user_id)

    filename = body.filename or "upload.bin"
    mime = body.mime or "application/octet-stream"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"

    photo_id = str(uuid.uuid4())
    key = f"{album_id}/{photo_id}.{ext}"

    # Create metadata now so list_photos can show it immediately
    now = int(time.time())
    table_photos.put_item(
        Item={
            "photo_id": photo_id,
            "album_id": album_id,
            "s3_key": key,
            "filename": filename,   # <-- store original name
            "uploaded_at": now,
        }
    )

    # Presigned PUT URL (browser uploads bytes directly to S3)
    put_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": mime},
        ExpiresIn=900,  # 15 minutes
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



@router.post("/photos/upload", status_code=status.HTTP_201_CREATED)
async def upload_photo_multipart(
    album_id_snake: Optional[str] = Form(None, alias="album_id"),
    album_id_camel: Optional[str] = Form(None, alias="albumId"),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    album_id = album_id_snake or album_id_camel
    if not album_id:
        raise HTTPException(status_code=422, detail="album_id is required")

    _assert_album_ownership(album_id, user_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Optional size guard
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (>{MAX_BYTES} bytes)")
    await file.seek(0)

    ext = (file.filename or "file").rsplit(".", 1)[-1]
    photo_id = str(uuid.uuid4())
    key = f"{album_id}/{photo_id}.{ext}"

    # Upload to S3; set ContentType for correct rendering
    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": file.content_type or "application/octet-stream",
        },
    )

    # Save metadata
    now = int(time.time())
    table_photos.put_item(
        Item={
            "photo_id": photo_id,
            "album_id": album_id,
            "s3_key": key,
            "filename": file.filename,  # <-- store original name
            "uploaded_at": now,
        }
    )

    # One-hour presigned GET URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return {
        "ok": True,
        "mode": "multipart",
        "photo_id": photo_id,
        "album_id": album_id,
        "s3_key": key,
        "uploaded_at": now,
        "url": url,
    }



@router.get("/photos/")
def list_photos(
    album_id: str = Query(...),
    limit: int = Query(10, gt=0),
    last_key: Optional[str] = Query(None),
    user_id: str = Depends(current_user),
):
    _assert_album_ownership(album_id, user_id)

    # Fetch all photos for this album via GSI
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


    items.sort(key=lambda p: p["uploaded_at"])

    # Offset if last_key provided
    start = 0
    if last_key:
        for i, p in enumerate(items):
            if p.get("photo_id") == last_key:
                start = i + 1
                break

    page = items[start : start + limit]

    for p in page:
        key = p["s3_key"]
        original = _safe_filename(p.get("filename") or key.rsplit("/", 1)[-1])

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
                "ResponseContentDisposition": f'attachment; filename="{original}"',
            },
            ExpiresIn=3600,
        )

    next_key = page[-1]["photo_id"] if page and (start + limit) < len(items) else None
    return {"items": page, "next_key": next_key}


@router.delete("/photos/{photo_id}", status_code=204)
def delete_photo(photo_id: str, user_id: str = Depends(current_user)):
    item = table_photos.get_item(Key={"photo_id": photo_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Photo not found")

    album = table_albums.get_item(Key={"album_id": item["album_id"]}).get("Item")
    if not album or album.get("owner") != user_id:
        raise HTTPException(status_code=403, detail="Not your photo")

    table_photos.delete_item(Key={"photo_id": photo_id})
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=item["s3_key"])
    except Exception:
        pass
