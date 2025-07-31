from fastapi import APIRouter, Depends
from boto3.dynamodb.conditions import Attr, Key
import time

from ..aws_config import dyna
from ..auth       import current_user

router       = APIRouter(prefix="/stats", tags=["stats"])
tbl_albums   = dyna.Table("Albums")
tbl_photos   = dyna.Table("PhotoMeta")

@router.get("/", summary="Simple usage metrics for the current user")
def my_stats(user_id: str = Depends(current_user)):
    #  albums owned by this user 
    alb_resp  = tbl_albums.scan(
        FilterExpression=Attr("owner").eq(user_id),
        ProjectionExpression="album_id"
    )
    album_ids = [a["album_id"] for a in alb_resp.get("Items", [])]
    album_cnt = len(album_ids)

    #  photos + storage for those albums 
    photo_cnt   = 0
    total_bytes = 0
    for aid in album_ids:
        ph_resp = tbl_photos.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(aid),
            ProjectionExpression="photo_id, size"
        )
        photo_cnt   += ph_resp["Count"]
        total_bytes += sum(int(p.get("size", 0)) for p in ph_resp.get("Items", []))

    return {
        "album_count":  album_cnt,
        "photo_count":  photo_cnt,
        "storage_mb":   round(total_bytes / 1_048_576, 1),  # MiB 1-decimal
        "ts":           int(time.time())
    }
