# app/routers/albums.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key
import time, uuid

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


class AlbumUpdate(BaseModel):
    title: str


class AlbumOut(BaseModel):
    album_id: str
    owner: str
    title: str
    created_at: int
    cover_url: str | None = None


@router.post(
    "/albums/",
    response_model=AlbumOut,
    status_code=status.HTTP_201_CREATED,
)
def create_album(
    title: str = Query(..., description="Title of the new album"),
    user_id: str = Depends(current_user),
):
    """
    Create a new album by passing ?title=… in the query string.
    """
    album_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "album_id": album_id,
        "owner": user_id,
        "title": title,
        "created_at": now,
        "cover_url": None,
    }
    table_albums.put_item(Item=item)
    return item


@router.get("/albums/", response_model=list[AlbumOut])
def list_albums(user_id: str = Depends(current_user)):
    """
    List all albums for the current user, with an optional cover_url.
    """
    resp = table_albums.scan(FilterExpression=Key("owner").eq(user_id))
    items = resp.get("Items", [])
    for alb in items:
        photo_resp = table_photos.scan(
            FilterExpression=Key("album_id").eq(alb["album_id"])
        )
        photos = photo_resp.get("Items", [])
        if photos:
            photos.sort(key=lambda x: x.get("uploaded_at", 0))
            s3_key = photos[0].get("s3_key")
            if s3_key:
                alb["cover_url"] = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET, "Key": s3_key},
                    ExpiresIn=3600,
                )
        else:
            alb["cover_url"] = None
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
        raise HTTPException(
            status_code=404, detail="Album not found or unauthorized"
        )

    table_albums.update_item(
        Key={"album_id": album_id},
        UpdateExpression="SET title = :t",
        ExpressionAttributeValues={":t": body.title},
    )
    item["title"] = body.title
    return item


@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: str,
    user_id: str = Depends(current_user),
):
    """
    Delete an album and all its photo metadata.
    """
    resp = table_albums.get_item(Key={"album_id": album_id})
    item = resp.get("Item")
    if not item or item["owner"] != user_id:
        raise HTTPException(
            status_code=404, detail="Album not found or unauthorized"
        )

    # Delete the album record
    table_albums.delete_item(Key={"album_id": album_id})

    # Cascade-delete any photos in this album
    photo_resp = table_photos.scan(
        FilterExpression=Key("album_id").eq(album_id)
    )
    for photo in photo_resp.get("Items", []):
        table_photos.delete_item(Key={"photo_id": photo["photo_id"]})
