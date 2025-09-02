# app/tokens.py
import os 
import time
import hmac
import hashlib
import secrets

JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure")

def new_token() -> tuple[str, str]:
    """
    Returns (raw_token, token_digest). Store only the digest in DB.
    """
    raw = secrets.token_urlsafe(32)
    digest = hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw, digest

def digest_token(raw: str) -> str:
    return hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()

def expiry_ts(minutes: int) -> int:
    return int(time.time()) + minutes * 60

def now_ts() -> int:
    return int(time.time())
