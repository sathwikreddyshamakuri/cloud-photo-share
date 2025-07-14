from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key
import time, uuid

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")

# Pydantic models
class AlbumCreate(BaseModel):
    title: str

class AlbumUpdate(BaseModel):
    title: str

class AlbumOut(BaseModel):
    album_id: str
    owner: str
    title: str
    created_at: int
    cover_url: str | None = None


@router.post("/albums/", response_model=AlbumOut, status_code=status.HTTP_201_CREATED)
def create_album(
    body: AlbumCreate,
    user_id: str = Depends(current_user),
):
    """
    Create a new album. Expects JSON body: { "title": "..." }.
    """
    album_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "album_id": album_id,
        "owner": user_id,
        "title": body.title,
        "created_at": now,
        "cover_url": None,
    }
    table_albums.put_item(Item=item)
    return item


@router.get("/albums/", response_model=list[AlbumOut])
def list_albums(user_id: str = Depends(current_user)):
    """
    List all albums for the current user.
    """
    resp = table_albums.scan(FilterExpression=Key("owner").eq(user_id))
    items = resp.get("Items", [])
    # Compute a cover_url from the first photo in each album
    for alb in items:
        photos = table_photos.scan(
            FilterExpression=Key("album_id").eq(alb["album_id"])
        ).get("Items", [])
        if photos:
            photos.sort(key=lambda x: x.get("uploaded_at", 0))
            s3_key = photos[0].get("s3_key")
            if s3_key:
                alb["cover_url"] = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET, "Key": s3_key},
                    ExpiresIn=3600,
                )
    return items


@router.put("/albums/{album_id}", response_model=AlbumOut)
def rename_album(
    album_id: str,
    body: AlbumUpdate,
    user_id: str = Depends(current_user),
):
    """
    Rename an existing album.
    """
    resp = table_albums.get_item(Key={"album_id": album_id})
    item = resp.get("Item")
    if not item or item["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found or unauthorized")
    table_albums.update_item(
        Key={"album_id": album_id},
        UpdateExpression="SET title = :t",
        ExpressionAttributeValues={":t": body.title},
    )
    item["title"] = body.title
    # Optionally regenerate cover_url here if desired
    return item


@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: str,
    user_id: str = Depends(current_user),
):
    """
    Delete an album and cascade-delete its photos.
    """
    resp = table_albums.get_item(Key={"album_id": album_id})
    item = resp.get("Item")
    if not item or item["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found or unauthorized")
    # Delete album record
    table_albums.delete_item(Key={"album_id": album_id})
    # Cascade delete photo metadata
    photos = table_photos.scan(
        FilterExpression=Key("album_id").eq(album_id)
    ).get("Items", [])
    for p in photos:
        table_photos.delete_item(Key={"photo_id": p["photo_id"]})
    return
