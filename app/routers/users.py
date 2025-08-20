# app/routers/users.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from pydantic import BaseModel, Field

# boto3 conditions are optional; only needed in Dynamo path
try:
    from boto3.dynamodb.conditions import Attr, Key  # type: ignore
except Exception:  # pragma: no cover
    Attr = None  # type: ignore
    Key = None  # type: ignore

from app.auth import current_user, get_user_by_id  # works for both backends

# Try to load AWS wiring; guard usage if in memory mode
try:
    from app.aws_config import dyna, s3, S3_BUCKET
except Exception:  # pragma: no cover
    dyna = None  # type: ignore
    s3 = None  # type: ignore
    S3_BUCKET = os.getenv("S3_BUCKET", "")  # type: ignore

router = APIRouter()
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")

# Dynamo tables (only valid if using dynamo backend)
table_users = dyna.Table("Users") if dyna else None  # type: ignore
table_albums = dyna.Table("Albums") if dyna else None  # type: ignore
table_photos = dyna.Table("PhotoMeta") if dyna else None  # type: ignore
table_tokens = dyna.Table("Tokens") if dyna else None  # type: ignore


class ProfileUpdateIn(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=40)
    bio: Optional[str] = Field(default=None, max_length=200)


@router.get("/users/me")
def get_me(user_id: str = Depends(current_user)):
    # Fetch user depending on backend
    if AUTH_BACKEND == "memory" or not table_users:
        item = get_user_by_id(user_id)
    else:
        resp = table_users.get_item(Key={"user_id": user_id})  # type: ignore[union-attr]
        item = resp.get("Item")

    if not item:
        raise HTTPException(status_code=404, detail="User not found")

    avatar_url: Optional[str] = None
    key = item.get("avatar_key")
    if key:
        if s3 and S3_BUCKET:
            try:
                avatar_url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET, "Key": key},
                    ExpiresIn=3600,
                )
            except Exception:
                avatar_url = None
        else:
            # local fallback: we store "avatars/<user_id>.png"
            avatar_url = f"{PUBLIC_API_URL}/static/{key}"

    return {
        "user_id": user_id,
        "email": item["email"],
        "display_name": item.get("display_name") or item["email"].split("@")[0],
        "bio": item.get("bio", ""),
        "avatar_url": avatar_url,
        "is_verified": bool(item.get("email_verified", item.get("is_verified", False))),
    }


@router.put("/users/me")
def update_me(data: ProfileUpdateIn, user_id: str = Depends(current_user)):
    if AUTH_BACKEND == "memory" or not table_users:
        item = get_user_by_id(user_id)
        if not item:
            raise HTTPException(status_code=404, detail="User not found")
        item["display_name"] = data.display_name
        item["bio"] = data.bio or ""
        # Save back to memory backend
        try:
            from app.auth import _put_user as _auth_put_user  # type: ignore
            _auth_put_user(item)
        except Exception:
            try:
                from app.auth import _mem_users  # type: ignore
                _mem_users[user_id] = item  # type: ignore[index]
            except Exception:
                pass
        return {"msg": "updated"}

    # Dynamo path
    resp = table_users.get_item(Key={"user_id": user_id})  # type: ignore[union-attr]
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")

    item["display_name"] = data.display_name
    item["bio"] = data.bio or ""
    table_users.put_item(Item=item)  # type: ignore[union-attr]
    return {"msg": "updated"}


@router.put("/users/me/avatar")
def update_avatar(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    # Local fallback when no S3
    if AUTH_BACKEND == "memory" or not s3 or not S3_BUCKET:
        root: Path = getattr(request.app.state, "local_upload_root", Path("local_uploads"))
        (root / "avatars").mkdir(parents=True, exist_ok=True)
        rel_key = f"avatars/{user_id}.png"
        out_path = root / rel_key
        with open(out_path, "wb") as f:
            f.write(contents)

        # update user record in memory
        item = get_user_by_id(user_id)
        if not item:
            raise HTTPException(status_code=404, detail="User not found")
        item["avatar_key"] = rel_key
        try:
            from app.auth import _put_user as _auth_put_user  # type: ignore
            _auth_put_user(item)
        except Exception:
            try:
                from app.auth import _mem_users  # type: ignore
                _mem_users[user_id] = item  # type: ignore[index]
            except Exception:
                pass

        return {"avatar_url": f"{PUBLIC_API_URL}/static/{rel_key}"}

    # Dynamo/S3 path
    key = f"avatars/{user_id}.png"
    s3.put_object(  # type: ignore[union-attr]
        Bucket=S3_BUCKET,
        Key=key,
        Body=contents,
        ContentType=file.content_type or "image/png",
    )

    # Update record
    resp = table_users.get_item(Key={"user_id": user_id})  # type: ignore[union-attr]
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    item["avatar_key"] = key
    table_users.put_item(Item=item)  # type: ignore[union-attr]

    url = s3.generate_presigned_url(  # type: ignore[union-attr]
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return {"avatar_url": url}


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user_id: str = Depends(current_user)):
    if AUTH_BACKEND == "memory" or not table_users:
        # memory cleanup only
        try:
            from app.auth import _mem_users, _mem_tokens  # type: ignore
            _mem_users.pop(user_id, None)
            for tok, data in list(_mem_tokens.items()):
                if data.get("user_id") == user_id:
                    _mem_tokens.pop(tok, None)
        except Exception:
            pass
        return  # 204

    # Dynamo path (unchanged)
    user = table_users.get_item(Key={"user_id": user_id}).get("Item")  # type: ignore[union-attr]
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    keys_to_delete = []
    if user.get("avatar_key"):
        keys_to_delete.append({"Key": user["avatar_key"]})

    albums = table_albums.scan(  # type: ignore[union-attr]
        FilterExpression=Attr("owner").eq(user_id)
    ).get("Items", [])

    for alb in albums:
        alb_id = alb["album_id"]
        photos = table_photos.query(  # type: ignore[union-attr]
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(alb_id),
        ).get("Items", [])

        for p in photos:
            if p.get("s3_key"):
                keys_to_delete.append({"Key": p["s3_key"]})
            table_photos.delete_item(Key={"photo_id": p["photo_id"]})  # type: ignore[union-attr]

        table_albums.delete_item(Key={"album_id": alb_id})  # type: ignore[union-attr]

    if table_tokens:
        toks = table_tokens.scan(  # type: ignore[union-attr]
            FilterExpression=Attr("user_id").eq(user_id)
        ).get("Items", [])
        for t in toks:
            table_tokens.delete_item(Key={"token": t["token"]})  # type: ignore[union-attr]

    table_users.delete_item(Key={"user_id": user_id})  # type: ignore[union-attr]

    if s3 and S3_BUCKET and keys_to_delete:
        while keys_to_delete:
            batch = keys_to_delete[:1000]
            keys_to_delete = keys_to_delete[1000:]
            try:
                s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": batch})
            except Exception:
                pass

    return  # 204
