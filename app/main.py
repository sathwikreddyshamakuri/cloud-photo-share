# app/main.py
import os, time, uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from boto3.dynamodb.conditions import Attr
from dotenv import load_dotenv, find_dotenv

from .auth import hash_pw, verify_pw, create_token, decode_token
from .routers import albums                      # router modules
import app.routers.photos as photos              # explicit import avoids circulars
from .aws_config import REGION, S3_BUCKET, s3, dyna  # shared AWS clients / constants

# DynamoDB tables
table_users  = dyna.Table("Users")
table_photos = dyna.Table("PhotoMeta")

# ── FastAPI app & routers ─────────────────────────────────────
app = FastAPI(title="Cloud Photo-Share API", version="0.5.0")
app.include_router(albums.router)
app.include_router(photos.router)

security = HTTPBearer()

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token")

# ── Health check ──────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

# ── Auth endpoints ────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

@app.post("/register")
def register(body: RegisterIn):
    if table_users.scan(FilterExpression=Attr("email").eq(body.email))["Items"]:
        raise HTTPException(status_code=400, detail="email already registered")
    user_id = str(uuid.uuid4())
    table_users.put_item(Item={
        "user_id": user_id,
        "email":   body.email,
        "password_hash": hash_pw(body.password),
    })
    return {"user_id": user_id}

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@app.post("/login")
def login(body: LoginIn):
    resp = table_users.scan(FilterExpression=Attr("email").eq(body.email))
    if not resp["Items"]:
        raise HTTPException(status_code=401, detail="user not found")
    user = resp["Items"][0]
    if not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="bad credentials")
    return {"access_token": create_token(user["user_id"])}

# ── Simple public feed (uploads handled in photos router) ─────
@app.get("/feed")
def get_feed(limit: int = 20):
    resp  = table_photos.scan()
    items = sorted(resp["Items"], key=lambda x: x["uploaded_at"], reverse=True)[:limit]
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )
    return {"photos": items}
