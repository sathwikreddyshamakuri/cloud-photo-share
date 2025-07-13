# app/routers/photos.py

import logging
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Query,
    HTTPException,
    Depends,
    status,
)
from boto3.dynamodb.conditions import Attr
import uuid
import time

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

logger = logging.getLogger(__name__)
router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


@router.post("/photos/", status_code=status.HTTP_201_CREATED)
def upload_photo(
    album_id: str = Query(..., description="Album ID to upload into"),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # ... your existing upload logic ...
    # unchanged
    ext = file.filename.split(".")[-1]
    s3_key = f"{album_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)

    photo_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "photo_id":    photo_id,
        "album_id":    album_id,
        "s3_key":      s3_key,
        "uploaded_at": now,
    }
    table_photos.put_item(Item=item)

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=3600,
    )
    return {**item, "url": url}


@router.get("/photos/")
def list_photos(
    album_id: str = Query(..., description="Album ID to filter by"),
    limit: int = Query(10, gt=0, description="Max number of photos to return"),
    last_key: str | None = Query(None, description="Photo ID to continue from"),
    user_id: str = Depends(current_user),
):
    try:
        # 1) Verify album exists & is owned by this user
        alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
        if not alb or alb["owner"] != user_id:
            raise HTTPException(status_code=404, detail="Album not found")

        # 2) Pull all photos for this album
        resp = table_photos.scan()
        photos = [it for it in resp.get("Items", []) if it["album_id"] == album_id]

        # 3) Sort by upload time so pagination is consistent
        photos.sort(key=lambda it: it["uploaded_at"])

        # 4) Locate start position
        start_index = 0
        if last_key:
            for idx, it in enumerate(photos):
                if it["photo_id"] == last_key:
                    start_index = idx + 1
                    break

        # 5) Slice out the current page
        page_items = photos[start_index : start_index + limit]

        # 6) Attach presigned URL to each item
        for it in page_items:
            try:
                it["url"] = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
                    ExpiresIn=3600,
                )
            except Exception as e:
                logger.exception("Failed to generate presigned URL for %s", it["photo_id"])
                it["url"] = None

        # 7) Compute next_key if more remain
        next_key = page_items[-1]["photo_id"] if (start_index + limit) < len(photos) else None

        return {"items": page_items, "next_key": next_key}

    except HTTPException:
        # re-raise 404s
        raise
    except Exception as e:
        logger.exception("Error in list_photos")
        raise HTTPException(status_code=500, detail="Unable to list photos")


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    user_id: str = Depends(current_user),
):
    # ... your existing delete logic ...
    resp = table_photos.get_item(Key={"photo_id": photo_id})
    if "Item" not in resp:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = resp["Item"]

    alb = table_albums.get_item(Key={"album_id": photo["album_id"]}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=403, detail="Not your photo")

    table_photos.delete_item(Key={"photo_id": photo_id})
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=photo["s3_key"])
    except Exception:
        pass

    return
