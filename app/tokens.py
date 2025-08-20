# app/tokens.py
import os
import time
import jwt  # PyJWT

_ALGO = "HS256"

def _secret() -> str:
    s = os.getenv("JWT_SECRET")
    if not s:
        raise RuntimeError("Set JWT_SECRET in your environment.")
    return s

def create_email_verify_token(user_id: str, email: str, ttl_seconds: int = 1800) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "scope": "verify",
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)

def decode_email_verify_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[_ALGO])
