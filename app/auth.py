# app/auth.py
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

# ---- choose a working JWT backend (PyJWT preferred; fall back to python-jose) ----
# _JWT: module with encode/decode; JWTError, ExpiredSig: exception classes
try:
    import jwt as _jwt  # expect PyJWT
    if not hasattr(_jwt, "encode") or not hasattr(_jwt, "decode"):
        raise ImportError("not PyJWT")
    from jwt import InvalidTokenError as JWTError, ExpiredSignatureError as ExpiredSig
    JWT_BACKEND = "pyjwt"
except Exception:
    try:
        from jose import jwt as _jwt  # python-jose
        from jose.exceptions import JWTError, ExpiredSignatureError as ExpiredSig
        JWT_BACKEND = "python-jose"
    except Exception as e:
        raise RuntimeError(
            "No usable JWT library found. Install PyJWT or python-jose."
        ) from e

# boto3 conditions used in Dynamo scan paths (guarded)
try:
    from boto3.dynamodb.conditions import Attr  # type: ignore
except Exception:  # pragma: no cover
    Attr = None  # type: ignore

# AWS wiring (guarded so memory mode works without AWS)
try:
    from .aws_config import dyna
except Exception:  # pragma: no cover
    dyna = None  # type: ignore

from .emailer import send_email


# Config
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()
AUTO_VERIFY = os.getenv("AUTO_VERIFY_USERS", "0") == "1"

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")  # set a strong one in prod
ALGORITHM = "HS256"
TOKEN_TTL = 60 * 60  # 1 hour

PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL", "")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Dynamo tables (only valid if using dynamo backend)
table_users = dyna.Table("Users") if dyna else None  # type: ignore
table_tokens = dyna.Table("Tokens") if dyna else None  # type: ignore

# In-memory stores for dev (AUTH_BACKEND=memory)
try:
    _mem_users  # type: ignore[name-defined]
except NameError:
    _mem_users: Dict[str, Dict[str, Any]] = {}

try:
    _mem_tokens  # type: ignore[name-defined]
except NameError:
    _mem_tokens: Dict[str, Dict[str, Any]] = {}


# Models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str


class VerifyIn(BaseModel):
    token: str


class ChangePwdIn(BaseModel):
    current_password: str
    new_password: str


# Helpers (hashing, JWT)
def hash_pw(p: str) -> str:
    return pwd_ctx.hash(p)


def verify_pw(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)


def create_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + TOKEN_TTL, "scope": "access"}
    token = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    # PyJWT returns str; python-jose returns str too; just ensure string
    return str(token)


def decode_token(token: str) -> str:
    try:
        data = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = data.get("sub")
        if not sub:
            raise JWTError("missing sub")
        return str(sub)
    except (JWTError, ExpiredSig):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(creds.credentials)


def _put_user(item: Dict[str, Any]) -> None:
    """Store a user in the active backend."""
    if AUTH_BACKEND == "memory" or not table_users:
        _mem_users[item["user_id"]] = item
    else:
        table_users.put_item(Item=item)  # type: ignore[union-attr]


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Public helper for routers."""
    if AUTH_BACKEND == "memory" or not table_users:
        return _mem_users.get(user_id)
    else:
        resp = table_users.get_item(Key={"user_id": user_id})  # type: ignore[union-attr]
        return resp.get("Item")


def _email_exists(email: str) -> bool:
    if AUTH_BACKEND == "memory" or not table_users:
        return any(u.get("email") == email for u in _mem_users.values())
    # Dynamo scan by email (use a GSI in real prod)
    resp = table_users.scan(  # type: ignore[union-attr]
        FilterExpression=Attr("email").eq(email) if Attr else None  # type: ignore[arg-type]
    )
    return bool(resp.get("Items"))


def _get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if AUTH_BACKEND == "memory" or not table_users:
        for u in _mem_users.values():
            if u.get("email") == email:
                return u
        return None
    resp = table_users.scan(  # type: ignore[union-attr]
        FilterExpression=Attr("email").eq(email) if Attr else None  # type: ignore[arg-type]
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def _new_one_time_token(user_id: str, kind: str, ttl_seconds: int = 3600) -> str:
    tok = str(uuid.uuid4())
    expires = int(time.time()) + ttl_seconds
    if AUTH_BACKEND == "memory" or not table_tokens:
        _mem_tokens[tok] = {"type": kind, "user_id": user_id, "expires_at": expires}
    else:
        table_tokens.put_item(  # type: ignore[union-attr]
            Item={"token": tok, "type": kind, "user_id": user_id, "expires_at": expires}
        )
    return tok


def _consume_token(token: str, kind: str) -> str:
    if AUTH_BACKEND == "memory" or not table_tokens:
        item = _mem_tokens.get(token)
        if not item or item.get("type") != kind or item.get("expires_at", 0) < time.time():
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        _mem_tokens.pop(token, None)
        return str(item["user_id"])
    resp = table_tokens.get_item(Key={"token": token})  # type: ignore[union-attr]
    item = resp.get("Item")
    if not item or item.get("type") != kind or item.get("expires_at", 0) < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    table_tokens.delete_item(Key={"token": token})  # type: ignore[union-attr]
    return str(item["user_id"])


# Handlers (register/login/reset/verify) – unchanged business logic
def register_user(body: RegisterIn):
    if _email_exists(body.email):
        raise HTTPException(status_code=400, detail="email already registered")

    user_id = str(uuid.uuid4())
    item: Dict[str, Any] = {
        "user_id": user_id,
        "email": body.email,
        "password_hash": hash_pw(body.password),
        "email_verified": AUTO_VERIFY,
    }
    _put_user(item)
    email_sent = False
    if not AUTO_VERIFY and PUBLIC_UI_URL:
        token = _new_one_time_token(user_id, "verify", 24 * 3600)
        verify_link = f"{PUBLIC_UI_URL}/verify?token={token}"
        try:
            send_email(
                to=body.email,
                subject="Verify your email",
                html=f"<p>Click to verify: <a href='{verify_link}'>{verify_link}</a></p>",
            )
            email_sent = True
        except Exception as e:  # pragma: no cover
            print("EMAIL ERROR:", e)

    return {
        "user_id": user_id,
        "email_sent": email_sent,
        "need_verify": not AUTO_VERIFY,
    }


def login_user(body: LoginIn):
    user = _get_user_by_email(body.email)
    if not user or not verify_pw(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="bad credentials")

    if not AUTO_VERIFY and not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="email not verified")

    return {"access_token": create_token(user["user_id"])}


def change_password(user_id: str, data: ChangePwdIn):
    item = get_user_by_id(user_id)
    if not item or not verify_pw(data.current_password, item.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="wrong password")
    item["password_hash"] = hash_pw(data.new_password)
    _put_user(item)
    return {"msg": "changed"}


def forgot_password(body: ForgotIn):
    user = _get_user_by_email(body.email)
    if user:
        tok = _new_one_time_token(user["user_id"], "reset", 3600)
        reset_url = f"{PUBLIC_UI_URL}/reset?token={tok}" if PUBLIC_UI_URL else ""
        if reset_url:
            try:
                send_email(
                    to=body.email,
                    subject="Reset your password",
                    html=f"<p>Reset link (1h): <a href='{reset_url}'>{reset_url}</a></p>",
                )
            except Exception as e:  # pragma: no cover
                print("EMAIL ERROR:", e)
    return {"msg": "If that email exists, a link was sent."}


def reset_password(body: ResetIn):
    user_id = _consume_token(body.token, "reset")
    item = get_user_by_id(user_id)
    if not item:
        raise HTTPException(status_code=404, detail="user not found")
    item["password_hash"] = hash_pw(body.new_password)
    _put_user(item)
    return {"msg": "password updated"}


def verify_email(body: VerifyIn):
    user_id = _consume_token(body.token, "verify")
    item = get_user_by_id(user_id)
    if not item:
        raise HTTPException(status_code=404, detail="user not found")
    item["email_verified"] = True
    _put_user(item)
    return {"msg": "verified"}
