# app/routers/account.py
from fastapi import APIRouter, Depends, Response
import os
import boto3
from boto3.dynamodb.conditions import Key
from app.auth import get_current_user

router = APIRouter(prefix="/account", tags=["account"])

_dynamo = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
_users  = _dynamo.Table(os.getenv("DDB_USER_TABLE", "Users"))
_albums = _dynamo.Table(os.getenv("DDB_ALBUM_TABLE", "Albums"))
_photos = _dynamo.Table(os.getenv("DDB_PHOTO_TABLE", "PhotoMeta"))

@router.delete("/", status_code=204)
def delete_account(user=Depends(get_current_user)):
    user_id = user["user_id"]

    # delete user row (ignore if already missing)
    try:
        _users.delete_item(Key={"user_id": user_id})
    except Exception:
        pass

    # delete albums owned by user (try owner-index, else scan)
    albums = []
    try:
        q = _albums.query(IndexName="owner-index", KeyConditionExpression=Key("owner").eq(user_id))
        albums = q.get("Items", [])
    except Exception:
        try:
            sc = _albums.scan()
            albums = [a for a in sc.get("Items", []) if a.get("owner") == user_id]
        except Exception:
            albums = []

    for a in albums:
        aid = a.get("album_id")
        if aid:
            try:
                _albums.delete_item(Key={"album_id": aid})
            except Exception:
                pass
            # delete photo meta for this album (use album_id-index; else scan)
            try:
                qs = _photos.query(IndexName="album_id-index", KeyConditionExpression=Key("album_id").eq(aid))
                items = qs.get("Items", [])
            except Exception:
                try:
                    scp = _photos.scan()
                    items = [p for p in scp.get("Items", []) if p.get("album_id") == aid]
                except Exception:
                    items = []

            for p in items:
                try:
                    _photos.delete_item(Key={"photo_id": p["photo_id"]})
                except Exception:
                    pass

    return Response(status_code=204)
