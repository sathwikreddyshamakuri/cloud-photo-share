# app/routers/auth_email.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
import os
import time
import boto3
from boto3.dynamodb.conditions import Key

from ..tokens import new_token, digest_token, expiry_ts, now_ts
from ..emailer import send_email, verification_email_html, reset_email_html


AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
USERS_TABLE = os.getenv("DYNAMO_USERS", "Users")

# Frontend (SPA) base URL, e.g., https://nuagevault.web.app or Vercel site
PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL", "http://localhost:5173")
# Public API base URL used in emails for server-first verification, e.g., your Render API
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))

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


# Fallback hasher if app.auth isn't present in local/dev
try:
    from app.auth import hash_password  # type: ignore
except Exception:
    import hashlib
    def hash_password(pwd: str) -> str:
        return hashlib.sha256(pwd.encode()).hexdigest()


def get_user_by_email(email: str) -> dict | None:
    """
    Requires a GSI named 'email-index' with partition key 'email' (string, lowercased).
    """
    resp = users.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email.lower()),
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


def _verify_token_and_mark(user: dict, raw_token: str):
    # Already verified? treat as success
    if user.get("email_verified"):
        return "already"

    # Expired?
    if int(time.time()) > int(user.get("email_verify_expires_at", 0)):
        return "expired"

    # Wrong token?
    if digest_token(raw_token) != user.get("email_verify_token_hash"):
        return "invalid"

    # Good → flip the flag
    mark_verified(user["user_id"])
    return "ok"


def _send_verification_email(email: str, raw_token: str):
    verify_url = f"{PUBLIC_API_URL}/auth/verify-email?token={raw_token}&email={email}"
    send_email(email, "Verify your email", verification_email_html(verify_url))


@router.post("/resend-verification")
def resend_verification(req: ForgotRequest):
    user = get_user_by_email(req.email)
    if not user:
        return {"ok": True}  # don't leak existence
    if user.get("email_verified"):
        return {"ok": True}

    raw, tok_hash = new_token()
    exp = expiry_ts(TOKEN_EXPIRE_MINUTES)
    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression="SET email_verify_token_hash = :h, email_verify_expires_at = :e",
        ExpressionAttributeValues={":h": tok_hash, ":e": exp},
    )
    _send_verification_email(req.email, raw)
    return {"ok": True}


# --------- NEW: server-first verification (click → backend → redirect) ----------
@router.get("/verify-email")
def verify_email_link(token: str, email: EmailStr):
    user = get_user_by_email(email)
    if not user:
        # Redirect to frontend status page
        return RedirectResponse(f"{PUBLIC_UI_URL}/verify-result?status=notfound", status_code=303)

    status = _verify_token_and_mark(user, token)
    return RedirectResponse(f"{PUBLIC_UI_URL}/verify-result?status={status}", status_code=303)


# Optional: plain HTML fallback that doesn't rely on your SPA at all
@router.get("/verify-email/plain")
def verify_email_plain(token: str, email: EmailStr):
    user = get_user_by_email(email)
    if not user:
        return HTMLResponse("<h1>Account not found.</h1>", status_code=404)

    status = _verify_token_and_mark(user, token)
    if status == "ok" or status == "already":
        return HTMLResponse("<h1>Email verified ✓</h1><p>You can close this tab and log in.</p>")
    elif status == "expired":
        return HTMLResponse("<h1>Link expired</h1><p>Please request a new verification email.</p>", status_code=410)
    else:
        return HTMLResponse("<h1>Invalid link</h1><p>Please request a new verification email.</p>", status_code=400)
# -------------------------------------------------------------------------------


# Kept for compatibility if your SPA still posts to verify explicitly
@router.post("/verify")
def verify_email(req: VerifyRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(404, "User not found")

    status = _verify_token_and_mark(user, req.token)
    if status in ("ok", "already"):
        return {"ok": True}
    elif status == "expired":
        raise HTTPException(400, "Verification token expired")
    else:
        raise HTTPException(400, "Invalid token")


@router.post("/forgot-password")
def forgot_password(req: ForgotRequest):
    user = get_user_by_email(req.email)
    if not user:
        return {"ok": True}  # avoid enumeration

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

    # NOTE: In DynamoDB UpdateExpression, operations must be ordered: SET ... REMOVE ...
    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression=(
            "SET password_hash = :ph "
            "REMOVE pwd_reset_token_hash, pwd_reset_expires_at"
        ),
        ExpressionAttributeValues={":ph": hash_password(req.new_password)},
    )
    return {"ok": True}
