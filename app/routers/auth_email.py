# app/routers/auth_email.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
import os
import time
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

from ..tokens import new_token, digest_token, expiry_ts, now_ts
from ..emailer import send_email, verification_email_html, reset_email_html

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
USERS_TABLE = os.getenv("DYNAMO_USERS", "Users")

# Frontend (SPA) base URL, e.g., https://nuagevault.app
PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL", "http://localhost:5173")
# Public API base URL (only used if you switch emails to server-first verify links)
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



try:
    from app.auth import hash_password  # type: ignore
except Exception:
    import hashlib
    def hash_password(pwd: str) -> str:
        return hashlib.sha256(pwd.encode()).hexdigest()



def get_user_by_email(email: str) -> dict | None:
    """
    Prefer the GSI 'email-index' (PK=email, String, lowercased). While the GSI
    is missing/CREATING, fall back to a table scan (fine for small tables).
    """
    e = (email or "").lower()

    # Fast path: Query the GSI
    try:
        resp = users.query(
            IndexName="email-index",
            KeyConditionExpression=Key("email").eq(e),
            Limit=1,
        )
        items = resp.get("Items") or []
        if items:
            return items[0]
    except ClientError:
        # GSI missing or not ready → fall through to scan
        pass
    except Exception:
        # Any transient issue → fall through to scan
        pass

    # Fallback: scan (keeps you unblocked while the GSI backfills)
    try:
        resp = users.scan(
            FilterExpression=Attr("email").eq(e),
            Limit=1,
        )
        items = resp.get("Items") or []
        return items[0] if items else None
    except ClientError as e:
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=500, detail=f"dynamo scan failed: {msg}")


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
    # Already verified?
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
    # You can keep using the frontend-first link, or switch to server-first:
    # verify_url = f"{PUBLIC_API_URL}/auth/verify-email?token={raw_token}&email={email}"
    verify_url = f"{PUBLIC_UI_URL}/verify?token={raw_token}&email={email}"
    send_email(email, "Verify your email", verification_email_html(verify_url))


# ---------- Routes ----------
@router.post("/resend-verification")
def resend_verification(req: ForgotRequest):
    user = get_user_by_email(req.email)
    if not user:
        return {"ok": True}  # avoid user enumeration
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



@router.get("/verify-email")
def verify_email_link(token: str, email: EmailStr):
    user = get_user_by_email(email)
    if not user:
        return RedirectResponse(f"{PUBLIC_UI_URL}/verify-result?status=notfound", status_code=303)

    status = _verify_token_and_mark(user, token)
    return RedirectResponse(f"{PUBLIC_UI_URL}/verify-result?status={status}", status_code=303)


@router.get("/verify-email/plain")
def verify_email_plain(token: str, email: EmailStr):
    user = get_user_by_email(email)
    if not user:
        return HTMLResponse("<h1>Account not found.</h1>", status_code=404)

    status = _verify_token_and_mark(user, token)
    if status in ("ok", "already"):
        return HTMLResponse("<h1>Email verified ✓</h1><p>You can close this tab and log in.</p>")
    elif status == "expired":
        return HTMLResponse("<h1>Link expired</h1><p>Please request a new verification email.</p>", status_code=410)
    else:
        return HTMLResponse("<h1>Invalid link</h1><p>Please request a new verification email.</p>", status_code=400)


# --- Frontend-first compatibility: POST /auth/verify with {email, token} ---
@router.post("/verify")
def verify_email(req: VerifyRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    status = _verify_token_and_mark(user, req.token)
    if status in ("ok", "already"):
        return {"ok": True}
    elif status == "expired":
        raise HTTPException(status_code=400, detail="Verification token expired")
    else:
        raise HTTPException(status_code=400, detail="Invalid token")


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
        raise HTTPException(status_code=400, detail="Invalid token")

    if int(time.time()) > int(user.get("pwd_reset_expires_at", 0)):
        raise HTTPException(status_code=400, detail="Token expired")

    if digest_token(req.token) != user.get("pwd_reset_token_hash"):
        raise HTTPException(status_code=400, detail="Invalid token")

    # DynamoDB UpdateExpression: SET before REMOVE
    users.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression=(
            "SET password_hash = :ph "
            "REMOVE pwd_reset_token_hash, pwd_reset_expires_at"
        ),
        ExpressionAttributeValues={":ph": hash_password(req.new_password)},
    )
    return {"ok": True}
