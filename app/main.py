# app/main.py
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, Response, Request
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


ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cloud-photo-share-y61e.vercel.app",
}
if PUBLIC_UI_URL:
    ALLOWED_ORIGINS.add(PUBLIC_UI_URL)

VERCEL_REGEX = r"^https://.*\.vercel\.app$"
VERCEL_RE = re.compile(VERCEL_REGEX)

ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
# List explicit headers to avoid any framework/version quirks
ALLOWED_HEADERS = "content-type, authorization, x-requested-with"

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_origin_regex=VERCEL_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # middleware will reflect requested headers
    expose_headers=["Content-Disposition"],
)

def _is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    return origin in ALLOWED_ORIGINS or bool(VERCEL_RE.match(origin))

def _cors_preflight_response(req: Request) -> Response:
    origin = req.headers.get("origin")
    acrh = req.headers.get("access-control-request-headers", "")
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }
    # echo requested headers or fall back to our list
    headers["Access-Control-Allow-Headers"] = acrh or ALLOWED_HEADERS
    if _is_allowed_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
    # 204 with headers—no body
    return Response(status_code=204, headers=headers)


@app.options("/{rest_of_path:path}")
def preflight_cors(rest_of_path: str, request: Request):
    return _cors_preflight_response(request)


if AUTH_BACKEND == "memory":
    LOCAL_UPLOAD_ROOT = Path(os.getenv("LOCAL_UPLOAD_ROOT", "local_uploads"))
    (LOCAL_UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
    app.state.local_upload_root = LOCAL_UPLOAD_ROOT
    app.mount("/static", StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)), name="static")


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


@app.get("/")
def root():
    return {"name": "Cloud Photo-Share API", "version": VERSION, "backend": AUTH_BACKEND}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/feed")
def get_feed(limit: int = 20):
    return {"photos": []}
