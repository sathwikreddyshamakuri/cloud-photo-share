# ── stdlib ─────────────────────────────────────────────────────
import os, time, uuid
from pathlib import Path

# ── FastAPI / Pydantic ────────────────────────────────────────
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# ── AWS + dotenv ──────────────────────────────────────────────
import boto3
from boto3.dynamodb.conditions import Attr
from dotenv import load_dotenv, find_dotenv

# ── local modules ─────────────────────────────────────────────
from .auth import hash_pw, verify_pw, create_token, decode_token
from .routers import albums                 # <── NEW: import the router module

# ──────────────────────────────── CONFIG ──────────────────────
load_dotenv(find_dotenv())
REGION     = os.getenv("REGION", "us-east-1")
S3_BUCKET  = os.getenv("S3_BUCKET")

s3   = boto3.client("s3",   region_name=REGION)
dyna = boto3.resource("dynamodb", region_name=REGION)

table_photos = dyna.Table("PhotoMeta")
table_users  = dyna.Table("Users")

# ──────────────────────────── APP SETUP ───────────────────────
app      = FastAPI(title="Cloud Photo-Share API", version="0.4.0")
security = HTTPBearer()

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")

# ──────────────── register albums router (NEW) ────────────────
app.include_router(albums.router)

# ──────────────────────────── ROUTES ──────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

# ----------  Auth endpoints  ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

@app.post("/register")
def register(body: RegisterIn):
    if table_users.scan(FilterExpression=Attr("email").eq(body.email))["Items"]:
        raise HTTPException(400, "email already registered")

    user_id = str(uuid.uuid4())
    table_users.put_item(Item={
        "user_id":       user_id,
        "email":         body.email,
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
        raise HTTPException(401, "user not found")

    user = resp["Items"][0]
    if not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "bad credentials")

    token = create_token(user["user_id"])
    return {"access_token": token}

# ----------  Photo upload & feed  ----------
@app.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    photo_id = str(uuid.uuid4())
    key      = f"photos/{photo_id}-{file.filename}"

    body = await file.read()
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=body,
        ContentType=file.content_type,
    )

    table_photos.put_item(Item={
        "photo_id":    photo_id,
        "s3_key":      key,
        "uploader":    user_id,
        "caption":     "",
        "uploaded_at": int(time.time()),
    })

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )
    return {"photo_id": photo_id, "url": url}

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
