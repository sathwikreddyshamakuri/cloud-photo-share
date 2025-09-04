from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional, List

# --- Robust PyJWT import (avoid "module 'jwt' has no attribute 'encode'") ---
try:
    from jwt import encode as jwt_encode, decode as jwt_decode, PyJWTError  # PyJWT
except Exception:  # pragma: no cover
    import jwt as _jwt  # fallback, but expect PyJWT to be installed
    jwt_encode = _jwt.encode
    jwt_decode = _jwt.decode
    PyJWTError = Exception

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

# Dynamo helpers
try:
    from boto3.dynamodb.conditions import Attr  # type: ignore
except Exception:  # pragma: no cover
    Attr = None  # type: ignore

try:
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover
    ClientError = Exception  # type: ignore

# AWS wiring (guarded so memory mode works without AWS)
try:
    from .aws_config import dyna
except Exception:  # pragma: no cover
    dyna = None  # type: ignore

from .emailer import send_email

AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()
AUTO_VERIFY = os.getenv("AUTO_VERIFY_USERS", "0") == "1"

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"
TOKEN_TTL = 60 * 60  # 1 hour

PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL", "")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Make bearer optional so we can fall back to cookie.
security = HTTPBearer(auto_error=False)

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

# -------------------- Models --------------------

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

# -------------------- Helpers --------------------

def hash_pw(p: str) -> str:
    return pwd_ctx.hash(p)

def verify_pw(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)

def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + TOKEN_TTL, "scope": "access"}
    return jwt_encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        data = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return str(data["sub"])
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Accept Bearer OR cookie named "access_token"
def current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    token = None
    if creds and getattr(creds, "credentials", None):
        token = creds.credentials
    else:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return decode_token(token)

# ---- Dynamo scan utility with pagination ----
def _dynamo_scan_all(table, **kwargs) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    last_key = None
    while True:
        params = {k: v for k, v in kwargs.items() if v is not None}
        if last_key:
            params["ExclusiveStartKey"] = last_key
        resp = table.scan(**params)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
    return items

def _put_user(item: Dict[str, Any]) -> None:
    if AUTH_BACKEND == "memory" or not table_users:
        _mem_users[item["user_id"]] = item
        return
    try:
        table_users.put_item(Item=item)  # type: ignore[union-attr]
    except ClientError as e:  # pragma: no cover
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo Users.put_item failed: {msg}")

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if AUTH_BACKEND == "memory" or not table_users:
        return _mem_users.get(user_id)
    try:
        resp = table_users.get_item(Key={"user_id": user_id})  # type: ignore[union-attr]
        return resp.get("Item")
    except ClientError as e:  # pragma: no cover
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo Users.get_item failed: {msg}")

def _scan_users_by_email(email: str) -> List[Dict[str, Any]]:
    if AUTH_BACKEND == "memory" or not table_users:
        return [u for u in _mem_users.values() if u.get("email") == email]
    try:
        if Attr is not None:
            resp = table_users.scan(FilterExpression=Attr("email").eq(email))  # type: ignore[union-attr]
            items = resp.get("Items", [])
            lek = resp.get("LastEvaluatedKey")
            while lek:
                resp = table_users.scan(FilterExpression=Attr("email").eq(email), ExclusiveStartKey=lek)  # type: ignore[union-attr]
                items.extend(resp.get("Items", []))
                lek = resp.get("LastEvaluatedKey")
            return items
        items = _dynamo_scan_all(table_users)  # type: ignore[arg-type]
        return [it for it in items if it.get("email") == email]
    except ClientError as e:  # pragma: no cover
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo Users.scan failed: {msg}")

def _email_exists(email: str) -> bool:
    return bool(_scan_users_by_email(email))

def _get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    items = _scan_users_by_email(email)
    return items[0] if items else None

def _new_one_time_token(user_id: str, kind: str, ttl_seconds: int = 3600) -> str:
    tok = str(uuid.uuid4())
    expires = int(time.time()) + ttl_seconds
    if AUTH_BACKEND == "memory" or not table_tokens:
        _mem_tokens[tok] = {"type": kind, "user_id": user_id, "expires_at": expires}
        return tok
    try:
        table_tokens.put_item(  # type: ignore[union-attr]
            Item={"token": tok, "type": kind, "user_id": user_id, "expires_at": expires}
        )
        return tok
    except ClientError as e:  # pragma: no cover
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo Tokens.put_item failed: {msg}")

def _consume_token(token: str, kind: str) -> str:
    if AUTH_BACKEND == "memory" or not table_tokens:
        item = _mem_tokens.get(token)
        if not item or item.get("type") != kind or item.get("expires_at", 0) < time.time():
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        _mem_tokens.pop(token, None)
        return str(item["user_id"])
    try:
        resp = table_tokens.get_item(Key={"token": token})  # type: ignore[union-attr]
        item = resp.get("Item")
        if not item or item.get("type") != kind or item.get("expires_at", 0) < time.time():
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        table_tokens.delete_item(Key={"token": token})  # type: ignore[union-attr]
        return str(item["user_id"])
    except ClientError as e:  # pragma: no cover
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo Tokens.get/delete failed: {msg}")

# -------------------- Handlers --------------------

def register_user(body: RegisterIn):
    try:
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
    except HTTPException:
        raise
    except ClientError as e:
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo error (register): {msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"register failed: {e!s}")

def login_user(body: LoginIn):
    try:
        user = _get_user_by_email(body.email)
        if not user or not verify_pw(body.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="bad credentials")

        if not AUTO_VERIFY and not user.get("email_verified", False):
            raise HTTPException(status_code=403, detail="email not verified")

        return {"access_token": create_token(user["user_id"])}
    except HTTPException:
        raise
    except ClientError as e:
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"dynamo error (login): {msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"login failed: {e!s}")
