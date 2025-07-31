# app/routers/stats.py
import math, time
from fastapi import APIRouter, Depends
from boto3.dynamodb.conditions import Attr, Key          
from ..aws_config import dyna, s3, S3_BUCKET
from ..auth import current_user

router = APIRouter(prefix="/stats", tags=["stats"])

tbl_albums = dyna.Table("Albums")
tbl_photos = dyna.Table("PhotoMeta")


@router.get("/", summary="Simple usage metrics for the current user")
def my_stats(user_id: str = Depends(current_user)):
    #   albums 
    alb_resp = tbl_albums.scan(
        FilterExpression=Attr("owner").eq(user_id),
        ProjectionExpression="album_id"
    )
    album_ids = [a["album_id"] for a in alb_resp.get("Items", [])]
    n_albums  = len(album_ids)

    # ── 2. photos & size ----------------------------------------------------
    # If your PhotoMeta items already have an `owner` attribute you can
    # skip the loop and just do a single scan:
    #
    # ph_resp   = tbl_photos.scan(FilterExpression=Attr("owner").eq(user_id),
    #                             ProjectionExpression="photo_id,size,s3_key")
    # photos    = ph_resp.get("Items", [])
    #
    photos, total_bytes = [], 0
    for aid in album_ids:
        ph_resp = tbl_photos.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(aid),
            ProjectionExpression="photo_id,size,s3_key"
        )
        photos.extend(ph_resp.get("Items", []))

    n_photos = len(photos)
    total_bytes = sum(int(p.get("size", 0)) for p in photos)
    storage_mb = round(total_bytes / 1_048_576, 1)  # one-decimal MiB

    return {
        "albums":      n_albums,
        "photos":      n_photos,
        "storage_mb":  storage_mb,
        "ts":          int(time.time())              
    }
