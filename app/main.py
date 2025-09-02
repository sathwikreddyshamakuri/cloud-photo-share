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
from app.routers import albums, photos, users, stats, auth_email, covers
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


VERSION = "0.7.2"  # bumped
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()


_public_ui = (os.getenv("PUBLIC_UI_URL") or "").strip().rstrip("/")
PUBLIC_UI_URL = _public_ui or None

app = FastAPI(title="Cloud Photo-Share API", version=VERSION)


# Exact origins we know about:
ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cloud-photo-share-y61e.vercel.app",
}
if PUBLIC_UI_URL:
    ALLOWED_ORIGINS.add(PUBLIC_UI_URL)

# Allow any *.vercel.app (handy for preview deployments)
VERCEL_REGEX = r"^https://.*\.vercel\.app$"
VERCEL_RE = re.compile(VERCEL_REGEX)

# Only used by our manual preflight below
ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
ALLOWED_HEADERS_FALLBACK = "content-type, authorization, x-requested-with"

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_origin_regex=VERCEL_REGEX,       # regex + explicit list
    allow_credentials=True,                # needed for cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],                   # let middleware reflect requested headers
    expose_headers=["Content-Disposition"] # for downloads
)

def _is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    # match exact or *.vercel.app
    return origin in ALLOWED_ORIGINS or bool(VERCEL_RE.match(origin))

def _cors_preflight_response(req: Request) -> Response:
    origin = req.headers.get("origin")
    acrh   = req.headers.get("access-control-request-headers", "")
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
        # reflect requested headers, or use sane fallback
        "Access-Control-Allow-Headers": acrh or ALLOWED_HEADERS_FALLBACK,
    }
    if _is_allowed_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
    # 204 with headers—no body
    return Response(status_code=204, headers=headers)

# Single catch-all preflight route (optional; CORSMiddleware can also handle OPTIONS)
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

@app.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": time.time()}

# Example placeholder feed (safe to keep)
@app.get("/feed")
def get_feed(limit: int = 20):
    return {"photos": []}

