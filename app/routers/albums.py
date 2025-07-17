# app/routers/albums.py
import uuid, time
from fastapi import APIRouter, Query, HTTPException, Depends, status
from boto3.dynamodb.conditions import Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


# ───────────────────────────── create album ────────────────────────────────
@router.post("/albums/", status_code=status.HTTP_201_CREATED)
def create_album(
    title: str = Query(..., description="Album title"),
    user_id: str = Depends(current_user),
):
    album_id = str(uuid.uuid4())
    now = int(time.time())
    table_albums.put_item(
        Item={
            "album_id": album_id,
            "title": title,
            "owner": user_id,
            "created_at": now,
        }
    )
    return {"album_id": album_id, "title": title, "created_at": now}


# ───────────────────────────── list albums ────────────────────────────────
@router.get("/albums/")
def list_albums(
    limit: int = Query(10, gt=0),
    last_key: str | None = Query(None),
    user_id: str = Depends(current_user),
):
    resp = table_albums.scan()
    items = [a for a in resp.get("Items", []) if a["owner"] == user_id]
    items.sort(key=lambda a: a["created_at"])
    return {"items": items[:limit]}


# ───────────────────────────── delete album ───────────────────────────────
@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: str, user_id: str = Depends(current_user)):
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    resp = table_photos.query(
        IndexName="album_id-index",
        KeyConditionExpression=Key("album_id").eq(album_id),
    )
    for p in resp.get("Items", []):
        table_photos.delete_item(Key={"photo_id": p["photo_id"]})
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=p["s3_key"])
        except Exception:
            pass

    table_albums.delete_item(Key={"album_id": album_id})
