# app/main.py
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import routers at the top (fixes E402)
from app.routers import albums, photos, users, account, stats

# util router is optional — import if present
try:
    from app.routers import util  # type: ignore
except Exception:
    util = None  # type: ignore

# Try to import your real auth code; otherwise provide stubs
try:
    from app.auth import RegisterIn, LoginIn, register_user, login_user  # type: ignore
except Exception:
    from pydantic import BaseModel

    class RegisterIn(BaseModel):
        email: str
        password: str
        name: str | None = None

    class LoginIn(BaseModel):
        email: str
        password: str

    def register_user(_: "RegisterIn"):
        return {"ok": False, "msg": "auth not wired"}

    def login_user(_: "LoginIn"):
        return {"ok": False, "msg": "auth not wired"}


# App

VERSION = "0.7.1"
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()
PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL")  # e.g., https://cloud-photo-share-y61e.vercel.app

app = FastAPI(title="Cloud Photo-Share API", version=VERSION)

# Local static for dev avatars — only when using memory backend
if AUTH_BACKEND == "memory":
    LOCAL_UPLOAD_ROOT = Path(os.getenv("LOCAL_UPLOAD_ROOT", "local_uploads"))
    (LOCAL_UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
    app.state.local_upload_root = LOCAL_UPLOAD_ROOT
    app.mount("/static", StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)), name="static")


# CORS

allow_origins = ["http://localhost:5173"]
if PUBLIC_UI_URL:
    allow_origins.append(PUBLIC_UI_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    allow_origins=allow_origins,   # exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers

if util:
    app.include_router(util.router, tags=["util"])

app.include_router(albums.router,  tags=["albums"])
app.include_router(photos.router,  tags=["photos"])
app.include_router(users.router,   tags=["users"])
app.include_router(account.router, tags=["auth-extra"])
app.include_router(stats.router,   tags=["stats"])

# Misc endpoints

@app.get("/")
def root():
    return {"name": "Cloud Photo-Share API", "version": VERSION, "backend": AUTH_BACKEND}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/register")
def register(body: RegisterIn):
    return register_user(body)

@app.post("/login")
def login(body: LoginIn):
    return login_user(body)

@app.get("/feed")
def get_feed(limit: int = 20):
    return {"photos": []}
