# app/main.py
from __future__ import annotations

import os
import time
from importlib import import_module
from pathlib import Path

from fastapi import FastAPI
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


VERSION = "0.7.4"
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "dynamo").lower().strip()

# Normalize PUBLIC_UI_URL (strip spaces and trailing slash)
_public_ui = (os.getenv("PUBLIC_UI_URL") or "").strip().rstrip("/")
PUBLIC_UI_URL = _public_ui or None

app = FastAPI(title="Cloud Photo-Share API", version=VERSION)

# --- CORS ---
ALLOWED_ORIGINS: set[str] = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://cloud-photo-share-y61e.vercel.app",
}
if PUBLIC_UI_URL:
    ALLOWED_ORIGINS.add(PUBLIC_UI_URL)

# Allow any *.vercel.app (useful for preview deployments)
VERCEL_REGEX = r"^https://.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_origin_regex=VERCEL_REGEX,  # regex + explicit list
    allow_credentials=True,           # needed for cookies
    allow_methods=["*"],              # let middleware handle OPTIONS & others
    allow_headers=["*"],              # reflect requested headers automatically
    expose_headers=["Content-Disposition"],  # for downloads
)


if AUTH_BACKEND == "memory":
    LOCAL_UPLOAD_ROOT = Path(os.getenv("LOCAL_UPLOAD_ROOT", "local_uploads"))
    (LOCAL_UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
    app.state.local_upload_root = LOCAL_UPLOAD_ROOT
    app.mount("/static", StaticFiles(directory=str(LOCAL_UPLOAD_ROOT)), name="static")

# --- Dynamic router loader (don’t crash boot if a router has issues) ---
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
_try_include(account, "auth-extra")  # guarded include
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


print("[BOOT] VERSION:", VERSION)
print("[BOOT] AUTH_BACKEND:", AUTH_BACKEND)
print("[BOOT] PUBLIC_UI_URL:", PUBLIC_UI_URL)
print("[BOOT] ALLOWED_ORIGINS:", ALLOWED_ORIGINS)
print("[BOOT] allow_origin_regex:", VERCEL_REGEX)
