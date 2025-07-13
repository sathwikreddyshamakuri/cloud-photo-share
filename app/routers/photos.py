# app/routers/photos.py

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

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


@router.post("/photos/", status_code=status.HTTP_201_CREATED)
def upload_photo(
    album_id: str = Query(..., description="Album ID to upload into"),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # 1) Verify album exists & is owned by this user
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

    # 2) Upload file to S3 under a unique key
    ext = file.filename.split(".")[-1]
    s3_key = f"{album_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)

    # 3) Record metadata in DynamoDB
    photo_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "photo_id":   photo_id,
        "album_id":   album_id,
        "s3_key":     s3_key,
        "uploaded_at": now,
    }
    table_photos.put_item(Item=item)

    # 4) Generate presigned URL and return it
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=3600,
    )
    return {**item, "url": url}


@router.get("/photos/")
def list_photos():
    resp = table_photos.scan()
    items = resp.get("Items", [])
    # Attach presigned URL
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )
    return {"items": items}


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    user_id: str = Depends(current_user),
):
    """
    Delete a photo by its ID, ensuring the current user owns the album.
    """
    # 1) Fetch the photo metadata
    resp = table_photos.get_item(Key={"photo_id": photo_id})
    if "Item" not in resp:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = resp["Item"]

    # 2) Verify ownership via the album
    alb = table_albums.get_item(Key={"album_id": photo["album_id"]}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=403, detail="Not your photo")

    # 3) Delete from DynamoDB
    table_photos.delete_item(Key={"photo_id": photo_id})

    # 4) Delete the object from S3
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=photo["s3_key"])
    except Exception:
        pass

    return
