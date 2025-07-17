# app/main.py
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos
from .aws_config import dyna, S3_BUCKET, s3   # noqa: F401  (import kept for future use)

app = FastAPI(title="Cloud Photo‑Share API", version="0.6.0")
import re, os

# ─────────────  CORS  ─────────────
app.add_middleware(
    CORSMiddleware,
    # Allow any https://cloud-photo-share-<slug>.vercel.app
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    # still allow your local dev server
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ──────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────

# Mount routers
app.include_router(albums.router, tags=["albums"])
app.include_router(photos.router, tags=["photos"])

# ─────────────────────────── Utility End‑points ──────────────────────────────
@app.get("/health")
def health():
    """Render uses this for its health‑check."""
    return {"status": "ok", "timestamp": time.time()}

@app.post("/register")
def register(body: RegisterIn):
    return register_user(body)

@app.post("/login")
def login(body: LoginIn):
    return login_user(body)

# Future feature — activity feed
@app.get("/feed")
def get_feed(limit: int = 20):
    # TODO: implement when we add social features
    return {"photos": []}
