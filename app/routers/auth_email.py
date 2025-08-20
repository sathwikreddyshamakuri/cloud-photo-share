# app/routers/auth_email.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, EmailStr
import os, time
import boto3

from app.tokens import new_token, digest_token, expiry_ts, now_ts
from app.emailer import send_email, verification_email_html, reset_email_html

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
USERS_TABLE = os.getenv("DYNAMO_USERS", "Users")
PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL", "http://localhost:5173")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))

ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
users = ddb.Table(USERS_TABLE)

router = APIRouter(prefix="/auth", tags=["auth"])



class VerifyRequest(BaseModel):
    email: EmailStr
    token: str

class ForgotRequest(BaseModel):
    email: EmailStr

class ResetRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str


try:
    from app.auth import hash_password  # type: ignore
except Exception:
    import hashlib
    def hash_password(pwd: str) -> str:  # Fallback: replace with your real hasher (bcrypt/argon2)
        return hashlib.sha256(pwd.encode()).hexdigest()



def get_user_by_email(email: str) -> dict | None:
    """
    Requires a GSI on 'email'. If your index name differs, update IndexName.
    """
    resp = users.query(
        IndexName="email-index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email.lower()),
        Limit=1,
    )
    items = resp.get("Items") or []
    return items[0] if items else None

def mark_verified(user_id: str):
    users.update_item(
        Key={"user_id": user_id},
        UpdateExpression=(
            "SET email_verified = :v, email_verified_at = :at "
            "REMOVE email_verify_token_hash, email_verify_expires_at"
        ),
        ExpressionAttributeValues={":v": True, ":at": now_ts()},
    )



@router.post("/resend-verification")
def resend_verification(req: ForgotRequest):
    user = get_user_by_email(req.email)
    if not user:
        return {"ok": True}  # don't leak whether user exists
    if user.get("email_verified"):
        return {"ok": True}

    raw, tok_hash = new_token()
    exp = expiry_ts(TOKEN_EXPIRE_MINUTES)
    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression="SET email_verify_token_hash = :h, email_verify_expires_at = :e",
        ExpressionAttributeValues={":h": tok_hash, ":e": exp},
    )
    verify_url = f"{PUBLIC_UI_URL}/verify?token={raw}&email={req.email}"
    send_email(req.email, "Verify your email", verification_email_html(verify_url))
    return {"ok": True}

@router.post("/verify")
def verify_email(req: VerifyRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("email_verified"):
        return {"ok": True}

    if int(time.time()) > int(user.get("email_verify_expires_at", 0)):
        raise HTTPException(400, "Verification token expired")

    if digest_token(req.token) != user.get("email_verify_token_hash"):
        raise HTTPException(400, "Invalid token")

    mark_verified(user["user_id"])
    return {"ok": True}

@router.post("/forgot-password")
def forgot_password(req: ForgotRequest):
    user = get_user_by_email(req.email)
    if not user:
        return {"ok": True}  # always 200 to avoid user enumeration

    raw, tok_hash = new_token()
    exp = expiry_ts(30)  # 30 minutes
    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression="SET pwd_reset_token_hash = :h, pwd_reset_expires_at = :e",
        ExpressionAttributeValues={":h": tok_hash, ":e": exp},
    )
    reset_url = f"{PUBLIC_UI_URL}/reset-password?token={raw}&email={req.email}"
    send_email(req.email, "Reset your password", reset_email_html(reset_url))
    return {"ok": True}

@router.post("/reset-password")
def reset_password(req: ResetRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(400, "Invalid token")

    if int(time.time()) > int(user.get("pwd_reset_expires_at", 0)):
        raise HTTPException(400, "Token expired")

    if digest_token(req.token) != user.get("pwd_reset_token_hash"):
        raise HTTPException(400, "Invalid token")

    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression=(
            "REMOVE pwd_reset_token_hash, pwd_reset_expires_at "
            "SET password_hash = :ph"
        ),
        ExpressionAttributeValues={":ph": hash_password(req.new_password)},
    )
    return {"ok": True}
