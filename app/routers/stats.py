from fastapi import APIRouter, Depends
from boto3.dynamodb.conditions import Attr
import time

from ..aws_config import dyna
from ..auth       import current_user

router       = APIRouter(prefix="/stats", tags=["stats"])
tbl_albums   = dyna.Table("Albums")
tbl_photos   = dyna.Table("PhotoMeta")


@router.get("/", summary="Usage metrics for the current user")
def my_stats(user_id: str = Depends(current_user)):
    #  albums owned by this user 
    alb_items = tbl_albums.scan(
        FilterExpression=Attr("owner").eq(user_id),
        ProjectionExpression="album_id"
    ).get("Items", [])
    album_ids   = {a["album_id"] for a in alb_items}
    album_count = len(album_ids)


    ph_items = tbl_photos.scan(
        ProjectionExpression="album_id, size"
    ).get("Items", [])

    my_photos = [p for p in ph_items if p.get("album_id") in album_ids]
    photo_count  = len(my_photos)
    total_bytes  = sum(int(p.get("size", 0)) for p in my_photos)
    storage_mb   = round(total_bytes / 1_048_576, 1)

    return {
        "album_count": album_count,
        "photo_count": photo_count,
        "storage_mb":  storage_mb,
        "ts":          int(time.time())
    }
