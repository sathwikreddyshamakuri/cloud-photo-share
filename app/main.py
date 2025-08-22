# app/main.py
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Routers
from app.routers import albums, photos, users, account, stats, auth_email, covers
try:
    from app.routers import util  # type: ignore
except Exception:
    util = None  # type: ignore

# Auth import (fallback stubs)
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


VERSION = "0.7.1"
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()
PUBLIC_UI_URL = os.getenv("PUBLIC_UI_URL")  # e.g., https://cloud-photo-share-y61e.vercel.app

app = FastAPI(title="Cloud Photo-Share API", version=VERSION)


# CORS

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cloud-photo-share-y61e.vercel.app",
]
# Allow preview deploys too
VERCEL_REGEX = r"https://.*\.vercel\.app"

if PUBLIC_UI_URL and PUBLIC_UI_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(PUBLIC_UI_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=VERCEL_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# Universal OPTIONS preflight (lets CORS middleware attach headers)

@app.options("/{rest_of_path:path}")
def preflight_cors(rest_of_path: str):
    return Response(status_code=204)


if AUTH_BACKEND == "memory":
    LOCAL_UPLOAD_ROOT = Path(os.getenv("LOCAL_UPLOAD_ROOT", "local_uploads"))
    (LOCAL_UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
    app.state.local_upload_root = LOCAL_UPLOAD_ROOT
    app.mount("/static", StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)), name="static")


# Routers

app.include_router(auth_email.router, tags=["auth-email"])
if util:
    app.include_router(util.router, tags=["util"])
app.include_router(albums.router, tags=["albums"])
app.include_router(photos.router, tags=["photos"])
app.include_router(users.router, tags=["users"])
app.include_router(account.router, tags=["auth-extra"])
app.include_router(stats.router, tags=["stats"])
app.include_router(covers.router, tags=["covers"])


@app.post("/register")
@app.post("/register/")
def register(body: RegisterIn):
    return register_user(body)

@app.post("/login")
@app.post("/login/")
def login(body: LoginIn):
    return login_user(body)


# Misc endpoints

@app.get("/")
def root():
    return {"name": "Cloud Photo-Share API", "version": VERSION, "backend": AUTH_BACKEND}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/feed")
def get_feed(limit: int = 20):
    return {"photos": []}
