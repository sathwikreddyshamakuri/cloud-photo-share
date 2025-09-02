from __future__ import annotations

from fastapi import APIRouter, Depends, status
from boto3.dynamodb.conditions import Attr, Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter(prefix="/account")

table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


def _list_user_albums(user_id: str):
    resp = table_albums.scan(FilterExpression=Attr("owner").eq(user_id))
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = table_albums.scan(
            FilterExpression=Attr("owner").eq(user_id),
            ExclusiveStartKey=resp["LastEvaluatedKey"],
        )
        items.extend(resp.get("Items", []))
    return items


def _list_album_photos(album_id: str):
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
    return items


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: str = Depends(current_user)):
    # Delete all albums (and photos) owned by this user.
    albums = _list_user_albums(user_id)
    for alb in albums:
        album_id = alb["album_id"]
        photos = _list_album_photos(album_id)

        # Delete S3 objects in batches (up to 1000 per call)
        if photos:
            objs = [{"Key": p["s3_key"]} for p in photos if "s3_key" in p]
            for i in range(0, len(objs), 1000):
                try:
                    s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objs[i:i+1000]})
                except Exception:
                    pass  # best-effort

        # Delete PhotoMeta rows
        for p in photos:
            try:
                table_photos.delete_item(Key={"photo_id": p["photo_id"]})
            except Exception:
                pass

        # Delete the album row
        try:
            table_albums.delete_item(Key={"album_id": album_id})
        except Exception:
            pass

    return None
