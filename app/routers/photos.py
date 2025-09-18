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
    HTTPException,
    Depends,
    status,
)
from boto3.dynamodb.conditions import Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")

# Optional size guard (defaults to 25 MB)
MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


@router.post("/photos/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    # Accept album id via query *or* form, and support both album_id & albumId
    album_id_q: Optional[str] = Query(None, alias="album_id"),
    album_id_q_camel: Optional[str] = Query(None, alias="albumId"),
    album_id_form: Optional[str] = Form(None, alias="album_id"),
    album_id_form_camel: Optional[str] = Form(None, alias="albumId"),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # Resolve album id from any of the above
    album_id = album_id_form or album_id_form_camel or album_id_q or album_id_q_camel
    if not album_id:
        # Return a flat message for easy UI display
        raise HTTPException(status_code=422, detail="album_id is required")

    # Ensure album exists and belongs to the current user
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb.get("owner") != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Optional size guard (only effective if server can read full body into memory)
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (>{MAX_BYTES} bytes)")
    # rewind for upload
    await file.seek(0)

    # Derive extension
    ext = (file.filename or "file").rsplit(".", 1)[-1]
    key = f"{album_id}/{uuid.uuid4()}.{ext}"

    # Upload to S3; set ContentType so browsers render correctly
    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
    )

    # Save metadata
    photo_id = str(uuid.uuid4())
    now = int(time.time())
    table_photos.put_item(
        Item={
            "photo_id": photo_id,
            "album_id": album_id,
            "s3_key": key,
            "uploaded_at": now,
        }
    )

    # One-hour presigned URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return {
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
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb.get("owner") != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

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

    # Oldest → newest
    items.sort(key=lambda p: p["uploaded_at"])

    # Offset if last_key provided
    start = 0
    if last_key:
        for i, p in enumerate(items):
            if p.get("photo_id") == last_key:
                start = i + 1
                break

    page = items[start : start + limit]

    # Attach URLs
    for p in page:
        p["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": p["s3_key"]},
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
        # soft-fail S3 delete; metadata already removed
        pass
