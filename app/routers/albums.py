# app/routers/albums.py
import uuid, time
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends, status, Body
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


# ---------- models ----------
class AlbumUpdateIn(BaseModel):
    title: str


# ---------- helpers ----------
def _album_item(album_id: str):
    return table_albums.get_item(Key={"album_id": album_id}).get("Item")


def _latest_photo_for_album(album_id: str) -> Optional[dict]:
    """Return the newest photo item (highest uploaded_at) or None."""
    resp = table_photos.query(
        IndexName="album_id-index",
        KeyConditionExpression=Key("album_id").eq(album_id),
        ScanIndexForward=False,  # newest first
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def _make_cover_url(photo_item: dict | None) -> Optional[str]:
    if not photo_item:
        return None
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": photo_item["s3_key"]},
            ExpiresIn=3600,
        )
    except Exception:  # pragma: no cover
        return None


# ---------- create album ----------
@router.post("/albums/", status_code=status.HTTP_201_CREATED)
def create_album(
    # Accept title in either JSON body or query param (UI-safe)
    title: str | None = Query(default=None, description="Album title (query)"),
    body: dict | None = Body(default=None),
    user_id: str = Depends(current_user),
):
    if body and "title" in body and not title:
        title = body["title"]
    if not title:
        raise HTTPException(400, "title is required")

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
    # no cover until a photo is uploaded
    return {
        "album_id": album_id,
        "title": title,
        "owner": user_id,
        "created_at": now,
        "cover_url": None,
    }


# ---------- list albums ----------
@router.get("/albums/")
def list_albums(
    limit: int = Query(50, gt=0),
    user_id: str = Depends(current_user),
):
    # scan then filter by owner (simple, fine for small tables)
    resp = table_albums.scan()
    items = [a for a in resp.get("Items", []) if a["owner"] == user_id]
    # sort oldest->newest (change if you prefer reverse)
    items.sort(key=lambda a: a["created_at"])

    # attach cover_url for each
    for a in items:
        p = _latest_photo_for_album(a["album_id"])
        a["cover_url"] = _make_cover_url(p)

    # slice to limit
    items = items[:limit]
    return {"items": items, "next_key": None}  # simple paging for now


# ---------- rename album ----------
@router.put("/albums/{album_id}", response_model=None)
def rename_album(
    album_id: str,
    data: AlbumUpdateIn,
    user_id: str = Depends(current_user),
):
    alb = _album_item(album_id)
    if not alb or alb["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    alb["title"] = data.title
    table_albums.put_item(Item=alb)  # overwrite
    # refresh cover (cheap reuse)
    p = _latest_photo_for_album(album_id)
    alb["cover_url"] = _make_cover_url(p)
    return alb


# ---------- delete album ----------
@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: str, user_id: str = Depends(current_user)):
    alb = _album_item(album_id)
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
