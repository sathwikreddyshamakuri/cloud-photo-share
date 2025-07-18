from fastapi import APIRouter, Depends, HTTPException
from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()
table_users = dyna.Table("Users")


@router.get("/users/me")
def get_me(user_id: str = Depends(current_user)):
    """Return the caller’s profile with a presigned avatar URL (if set)."""
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "User not found")

    avatar_url = None
    if key := item.get("avatar_key"):
        # 1‑hour presigned link
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
