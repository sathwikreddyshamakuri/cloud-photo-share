from ..auth import current_user
# app/routers/covers.py
import os
import boto3
from fastapi import APIRouter, Depends, HTTPException
from boto3.dynamodb.conditions import Key
from app.s3util import sign_key


router = APIRouter(prefix="/albums", tags=["covers"])

_dynamo = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
_photo_table = _dynamo.Table(os.getenv("DDB_PHOTO_TABLE", "PhotoMeta"))

@router.get("/{album_id}/cover")
def get_album_cover(album_id: str, _: str = Depends(current_user)):
    # latest photo in this album (GSI: album_id-index)
    try:
        q = _photo_table.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(album_id),
            ScanIndexForward=False,  # newest first
            Limit=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"dynamo query failed: {e}")

    items = q.get("Items", [])
    if not items:
        return {"url": None}

    photo = items[0]
    key = photo.get("s3_key") or photo.get("key")
    if not key:
        return {"url": None}

    try:
        url = sign_key(key, expires=3600)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"s3 sign failed: {e}")

