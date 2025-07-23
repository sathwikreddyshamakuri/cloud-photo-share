# app/main.py
import time
import re
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import photos, albums, users
from .routers import account
app.include_router(account.router)

#  Auth helpers 
from .auth import RegisterIn, LoginIn, register_user, login_user

# Keep S3/dynamo objects imported so other modules can import main.py if needed
from .aws_config import dyna, S3_BUCKET, s3  # noqa: F401

#  FastAPI app instance
app = FastAPI(title="Cloud Photo‑Share API", version="0.6.0")

# CORS settings 
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.routers import photos, albums  # noqa: E402

app.include_router(albums.router, tags=["albums"])
app.include_router(photos.router, tags=["photos"])
app.include_router(users.router,  tags=["users"])

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/register")
def register(body: RegisterIn):
    return register_user(body)


@app.post("/login")
def login(body: LoginIn):
    return login_user(body)


# Placeholder for future social feed
@app.get("/feed")
def get_feed(limit: int = 20):
    # TODO: implement when social features arrive
    return {"photos": []}
