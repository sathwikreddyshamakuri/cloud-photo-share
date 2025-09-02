# app/main.py
from __future__ import annotations

import os
import re
import time
from importlib import import_module
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


try:
    from app.auth import LoginIn, RegisterIn, login_user, register_user  # type: ignore
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


VERSION = "0.7.3"
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()


_public_ui = (os.getenv("PUBLIC_UI_URL") or "").strip().rstrip("/")
PUBLIC_UI_URL = _public_ui or None

app = FastAPI(title="Cloud Photo-Share API", version=VERSION)


ALLOWED_ORIGINS: set[str] = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cloud-photo-share-y61e.vercel.app",
}
if PUBLIC_UI_URL:
    ALLOWED_ORIGINS.add(PUBLIC_UI_URL)

# Allow any *.vercel.app (for preview deploys)
VERCEL_REGEX = r"^https://.*\.vercel\.app$"
VERCEL_RE = re.compile(VERCEL_REGEX)

# Preflight helpers
ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
ALLOWED_HEADERS_FALLBACK = "content-type, authorization, x-requested-with"

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_origin_regex=VERCEL_REGEX,
    allow_credentials=True,  # cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
        "Access-Control-Allow-Headers": acrh or ALLOWED_HEADERS_FALLBACK,
    }
    if _is_allowed_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
    return Response(status_code=204, headers=headers)


@app.options("/{rest_of_path:path}")
def preflight_cors(rest_of_path: str, request: Request):
    return _cors_preflight_response(request)



if AUTH_BACKEND == "memory":
    LOCAL_UPLOAD_ROOT = Path(os.getenv("LOCAL_UPLOAD_ROOT", "local_uploads"))
    (LOCAL_UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
    app.state.local_upload_root = LOCAL_UPLOAD_ROOT
    app.mount("/static", StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)), name="static")


def _import_optional(modpath: str):
    """Import a module if available; return None on failure (don’t crash boot)."""
    try:
        return import_module(modpath)
    except Exception as e:
        print(f"[BOOT] Optional router '{modpath}' not loaded: {e}")
        return None


def _try_include(mod, tag: str):
    """Include FastAPI router if the module exposes `router`."""
    try:
        if mod is None:
            return
        r = getattr(mod, "router", None)
        if r:
            app.include_router(r, tags=[tag])
        else:
            print(f"[BOOT] Module has no `router`: {mod}")
    except Exception as e:
        print(f"[BOOT] Skipping router {tag}: {e}")



albums = _import_optional("app.routers.albums")
photos = _import_optional("app.routers.photos")
users = _import_optional("app.routers.users")
account = _import_optional("app.routers.account")
stats = _import_optional("app.routers.stats")
auth_email = _import_optional("app.routers.auth_email")
covers = _import_optional("app.routers.covers")
util = _import_optional("app.routers.util")


_try_include(auth_email, "auth-email")
_try_include(util, "util")
_try_include(albums, "albums")
_try_include(photos, "photos")
_try_include(users, "users")
_try_include(account, "auth-extra")  # guarded, fixes Render error
_try_include(stats, "stats")
_try_include(covers, "covers")


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



@app.get("/feed")
def get_feed(limit: int = 20):
    return {"photos": []}

