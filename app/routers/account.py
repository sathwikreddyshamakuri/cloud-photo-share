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
    # delete photos (DDB + S3) for all of the user's albums, then the albums
    albums = _list_user_albums(user_id)
    for alb in albums:
        album_id = alb["album_id"]
        photos = _list_album_photos(album_id)

        # delete S3 objects in batches (up to 1000 per call)
        if photos:
            objs = [{"Key": p["s3_key"]} for p in photos if "s3_key" in p]
            for i in range(0, len(objs), 1000):
                try:
                    s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objs[i:i+1000]})
                except Exception:
                    pass  # best-effort delete

        # delete PhotoMeta items
        for p in photos:
            try:
                table_photos.delete_item(Key={"photo_id": p["photo_id"]})
            except Exception:
                pass

        # delete the album record
        try:
            table_albums.delete_item(Key={"album_id": album_id})
        except Exception:
            pass

    # 204 No Content
    return None
