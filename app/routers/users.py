# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from boto3.dynamodb.conditions import Attr, Key

from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()
table_users   = dyna.Table("Users")
table_albums  = dyna.Table("Albums")
table_photos  = dyna.Table("PhotoMeta")
table_tokens  = dyna.Table("Tokens")  # optional cleanup

class ProfileUpdateIn(BaseModel):
    display_name: constr(strip_whitespace=True, min_length=1, max_length=40)
    bio: constr(max_length=200) | None = None


@router.get("/users/me")
def get_me(user_id: str = Depends(current_user)):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "User not found")

    avatar_url = None
    if key := item.get("avatar_key"):
        avatar_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )

    return {
        "user_id":      user_id,
        "email":        item["email"],
        "display_name": item.get("display_name") or item["email"].split("@")[0],
        "bio":          item.get("bio", ""),
        "avatar_url":   avatar_url,
    }


@router.put("/users/me")
def update_me(data: ProfileUpdateIn, user_id: str = Depends(current_user)):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "User not found")
    item["display_name"] = data.display_name
    item["bio"] = data.bio or ""
    table_users.put_item(Item=item)
    return {"msg": "updated"}


@router.put("/users/me/avatar")
def update_avatar(file: bytes = Depends(), user_id: str = Depends(current_user)):  # keep your existing version if different
    raise HTTPException(501, "Not implemented here")  # placeholder so this snippet compiles if you already moved avatar


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user_id: str = Depends(current_user)):
    # Load user
    user = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not user:
        raise HTTPException(404, "User not found")

    # Collect avatar key if any
    keys_to_delete = []
    if user.get("avatar_key"):
        keys_to_delete.append({"Key": user["avatar_key"]})

    #  Find all albums owned by user
    # No GSI on owner, so we scan
    albums = table_albums.scan(
        FilterExpression=Attr("owner").eq(user_id)
    ).get("Items", [])

    # For each album, get all photos and queue S3 deletes + DB deletes
    for alb in albums:
        alb_id = alb["album_id"]
        # Query photos by album_id GSI
        photos = table_photos.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(alb_id)
        ).get("Items", [])

        # enqueue photo s3 keys
        for p in photos:
            if p.get("s3_key"):
                keys_to_delete.append({"Key": p["s3_key"]})

        # delete photo rows
        for p in photos:
            table_photos.delete_item(Key={"photo_id": p["photo_id"]})

        # delete album row
        table_albums.delete_item(Key={"album_id": alb_id})

    #  Delete tokens owned by this user (optional cleanup)
    toks = table_tokens.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    ).get("Items", [])
    for t in toks:
        table_tokens.delete_item(Key={"token": t["token"]})

    #  Delete user row
    table_users.delete_item(Key={"user_id": user_id})

    #  Delete objects from S3 in batches of 1000
    while keys_to_delete:
        batch = keys_to_delete[:1000]
        keys_to_delete = keys_to_delete[1000:]
        s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": batch})  # ignore errors quietly

    return  # 204
