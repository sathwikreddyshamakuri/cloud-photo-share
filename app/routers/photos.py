# app/routers/photos.py
import uuid
import time
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Depends, status
from boto3.dynamodb.conditions import Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")



@router.post("/photos/", status_code=status.HTTP_201_CREATED)
def upload_photo(
    album_id: str = Query(...),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    ext = (file.filename or "file").rsplit(".", 1)[-1]
    key = f"{album_id}/{uuid.uuid4()}.{ext}"

    # Ensure browser can render correctly by setting ContentType
    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
    )

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
    last_key: str | None = Query(None),
    user_id: str = Depends(current_user),
):
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # Fetch *all* photos for this album
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

    # Chronological order
    items.sort(key=lambda p: p["uploaded_at"])

    # Offset if last_key provided
    start = 0
    if last_key:
        for i, p in enumerate(items):
            if p["photo_id"] == last_key:
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

    next_key = page[-1]["photo_id"] if (start + limit) < len(items) else None
    return {"items": page, "next_key": next_key}



@router.delete("/photos/{photo_id}", status_code=204)
def delete_photo(photo_id: str, user_id: str = Depends(current_user)):
    item = table_photos.get_item(Key={"photo_id": photo_id}).get("Item")
    if not item:
        raise HTTPException(404, "Photo not found")

    album = table_albums.get_item(Key={"album_id": item["album_id"]}).get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(403, "Not your photo")

    table_photos.delete_item(Key={"photo_id": photo_id})
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=item["s3_key"])
    except Exception:
        pass
