from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
import time
import uuid

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET
from boto3.dynamodb.conditions import Attr

# Use a single Albums table for both listing and creation
table_albums = dyna.Table("Albums")
router = APIRouter()

class AlbumIn(BaseModel):
    title: str

@router.get("/albums/")
def list_albums(q: str = Query(None, description="Optional title filter")):
    # 1) Scan albums, optionally filter by title substring
    scan_kwargs = {}
    if q:
        scan_kwargs["FilterExpression"] = Attr("title").contains(q)
    resp = table_albums.scan(**scan_kwargs)
    albums = resp.get("Items", [])

    enriched = []
    for album in albums:
        # 2) Find photos in this album
        photos_resp = dyna.Table("PhotoMeta").scan(
            FilterExpression=Attr("album_id").eq(album["album_id"])
        )
        photos = photos_resp.get("Items", [])

        # 3) Pick the latest photo as cover
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

        # 4) Merge it in under `cover_url`
        enriched.append({**album, "cover_url": cover_url})

    return {"albums": enriched}

@router.post("/albums/", status_code=status.HTTP_201_CREATED)
def create_album(
    title: str = Query(..., description="Album title"),
    user_id: str = Depends(current_user),
):
    """
    Create a new album owned by the current user.
    Title is passed as a query parameter for compatibility with tests.
    """
    new_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "owner": user_id,
        "album_id": new_id,
        "title": title,
        "created_at": now,
    }
    table_albums.put_item(Item=item)
    # Return the created album, including cover_url = null
    return {**item, "cover_url": None}
