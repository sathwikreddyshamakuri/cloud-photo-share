# app/main.py

import time
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos
from .aws_config import dyna, S3_BUCKET, s3

# 1) Create the app
app = FastAPI(title="Cloud Photo-Share API", version="0.5.0")

# 2) Immediately add CORS middleware, before including any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow all origins in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Now include your routers
app.include_router(albums.router)
app.include_router(photos.router)

# 4) Health check
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

# 5) Auth
@app.post("/register")
def register(body: RegisterIn):
    return register_user(body)

@app.post("/login")
def login(body: LoginIn):
    return login_user(body)

# 6) Public feed
@app.get("/feed")
def get_feed(limit: int = 20):
    table_photos = dyna.Table("PhotoMeta")
    resp = table_photos.scan()
    items = sorted(resp["Items"], key=lambda x: x["uploaded_at"], reverse=True)[:limit]
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )
    return {"photos": items}
