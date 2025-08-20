# app/routers/users.py
from __future__ import annotations

import time
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, constr
from boto3.dynamodb.conditions import Attr, Key

from app.auth import current_user
from app.aws_config import dyna, s3, S3_BUCKET
from app.emailer import send_email
from app.tokens import create_email_verify_token, decode_email_verify_token

router = APIRouter()

# Dynamo tables (adjust names to match your infra if needed)
table_users = dyna.Table("Users")
table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")
table_tokens = dyna.Table("Tokens")  # optional cleanup table; safe if unused


class ProfileUpdateIn(BaseModel):
    display_name: constr(strip_whitespace=True, min_length=1, max_length=40)
    bio: Optional[constr(max_length=200)] = None




def _public_ui_url() -> str:
    return os.getenv("PUBLIC_UI_URL", "http://localhost:5173").rstrip("/")



@router.get("/users/me")
def get_me(user_id: str = Depends(current_user)):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")

    avatar_url = None
    key = item.get("avatar_key")
    if key:
        avatar_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )

    return {
        "user_id": user_id,
        "email": item["email"],
        "display_name": item.get("display_name") or item["email"].split("@")[0],
        "bio": item.get("bio", ""),
        "avatar_url": avatar_url,
        "is_verified": bool(item.get("is_verified", False)),
    }


@router.put("/users/me")
def update_me(data: ProfileUpdateIn, user_id: str = Depends(current_user)):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")

    item["display_name"] = data.display_name
    item["bio"] = data.bio or ""
    table_users.put_item(Item=item)
    return {"msg": "updated"}


@router.put("/users/me/avatar")
def update_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    # store at a deterministic key per-user
    key = f"avatars/{user_id}.png"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=contents,
        ContentType=file.content_type or "image/png",
    )

    # update user record
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    item["avatar_key"] = key
    table_users.put_item(Item=item)

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return {"avatar_url": url}


@router.post("/users/me/send-verification")
def send_verification_email(user_id: str = Depends(current_user)):
    """Send (or resend) a verification email to the current user."""
    user = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_email_verify_token(
        user_id=str(user["user_id"]), email=user["email"], ttl_seconds=1800
    )
    verify_link = f"{_public_ui_url()}/verify?token={token}"

    send_email(
        to=user["email"],
        subject="Verify your email",
        html=(
            "<h2>Welcome to Cloud Photo Share</h2>"
            f"<p>Please verify your email by clicking "
            f"<a href='{verify_link}'>this link</a> (valid for 30 minutes).</p>"
        ),
    )
    return {"ok": True}


@router.get("/users/verify")
def verify_email(token: str):
    """Verify a user's email using a signed token."""
    try:
        payload = decode_email_verify_token(token)
        if payload.get("scope") != "verify":
            raise ValueError("Invalid token scope")
        user_id = str(payload["sub"])
        email = payload["email"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or expired token: {e}")

    # mark verified
    table_users.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET is_verified = :v, verified_at = :t",
        ExpressionAttributeValues={":v": True, ":t": int(time.time())},
    )
    return {"ok": True, "user_id": user_id, "email": email}


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user_id: str = Depends(current_user)):
    # Load user
    user = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # collect avatar key if any
    keys_to_delete = []
    if user.get("avatar_key"):
        keys_to_delete.append({"Key": user["avatar_key"]})

    # Find all albums owned by user (no GSI on owner => scan)
    albums = table_albums.scan(
        FilterExpression=Attr("owner").eq(user_id)
    ).get("Items", [])

    # For each album, remove its photos (S3+DB), then the album
    for alb in albums:
        alb_id = alb["album_id"]

        photos = table_photos.query(
            IndexName="album_id-index",
            KeyConditionExpression=Key("album_id").eq(alb_id),
        ).get("Items", [])

        for p in photos:
            if p.get("s3_key"):
                keys_to_delete.append({"Key": p["s3_key"]})
            table_photos.delete_item(Key={"photo_id": p["photo_id"]})

        table_albums.delete_item(Key={"album_id": alb_id})

    # Optional: delete tokens owned by the user (ignore failures)
    try:
        toks = table_tokens.scan(
            FilterExpression=Attr("user_id").eq(user_id)
        ).get("Items", [])
        for t in toks:
            table_tokens.delete_item(Key={"token": t["token"]})
    except Exception:
        pass

    # Delete user row
    table_users.delete_item(Key={"user_id": user_id})

    # Delete S3 objects in batches of 1000
    while keys_to_delete:
        batch = keys_to_delete[:1000]
        keys_to_delete = keys_to_delete[1000:]
        try:
            s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": batch})
        except Exception:
            # ignore S3 delete errors in user delete flow
            pass

    return  # 204
