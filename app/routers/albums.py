# app/routers/albums.py

from fastapi import (
    APIRouter,
    Depends,
    Body,
    HTTPException,
    status,
)
from pydantic import BaseModel
from boto3.dynamodb.conditions import Attr
import time, uuid

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()
table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


class AlbumIn(BaseModel):
    title: str


@router.get("/albums/")
def list_albums():
    resp = table_albums.scan()
    items = resp.get("Items", [])

    enriched = []
    for alb in items:
        pr = table_photos.scan(
            FilterExpression=Attr("album_id").eq(alb["album_id"])
        )
        photos = pr.get("Items", [])
        if photos:
            photos.sort(key=lambda x: x["uploaded_at"], reverse=True)
            cover_key = photos[0]["s3_key"]
            cover_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": cover_key},
                ExpiresIn=3600,
            )
        else:
            cover_url = None
        enriched.append({**alb, "cover_url": cover_url})

    return {"albums": enriched}


@router.post("/albums/", status_code=201)
def create_album(
    body: AlbumIn = Body(...),
    user_id: str = Depends(current_user),
):
    new_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "owner":      user_id,
        "album_id":   new_id,
        "title":      body.title,
        "created_at": now,
    }
    table_albums.put_item(Item=item)
    return {**item, "cover_url": None}


@router.put("/albums/{album_id}", status_code=200)
def update_album(
    album_id: str,
    body: AlbumIn = Body(...),
    user_id: str = Depends(current_user),
):
    resp = table_albums.get_item(Key={"album_id": album_id})
    if "Item" not in resp:
        raise HTTPException(status_code=404, detail="Album not found")
    if resp["Item"]["owner"] != user_id:
        raise HTTPException(status_code=403, detail="Not your album")

    table_albums.update_item(
        Key={"album_id": album_id},
        UpdateExpression="SET title = :t",
        ExpressionAttributeValues={":t": body.title},
    )
    updated = table_albums.get_item(Key={"album_id": album_id})["Item"]
    return {**updated, "cover_url": None}


@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: str,
    user_id: str = Depends(current_user),
):
    resp = table_albums.get_item(Key={"album_id": album_id})
    if "Item" not in resp:
        raise HTTPException(status_code=404, detail="Album not found")
    if resp["Item"]["owner"] != user_id:
        raise HTTPException(status_code=403, detail="Not your album")

    # delete album metadata
    table_albums.delete_item(Key={"album_id": album_id})
    # (Optionally: cascade delete photos & S3 objects here.)
    return
