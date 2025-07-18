# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()
table_users = dyna.Table("Users")


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
        "user_id": user_id,
        "email": item["email"],
        "display_name": item.get("display_name") or item["email"].split("@")[0],
        "bio": item.get("bio", ""),
        "avatar_url": avatar_url,
    }


@router.put("/users/me")
def update_me(
    data: ProfileUpdateIn,
    user_id: str = Depends(current_user),
):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "User not found")

    item["display_name"] = data.display_name
    item["bio"] = data.bio or ""
    table_users.put_item(Item=item)
    return {"msg": "updated"}
