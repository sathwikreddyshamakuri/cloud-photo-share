from __future__ import annotations

import os
import re
import time
import logging
from importlib import import_module
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

try:
    from app.auth import LoginIn, RegisterIn, login_user, register_user, TOKEN_TTL  # type: ignore
except Exception:
    from pydantic import BaseModel
    TOKEN_TTL = 3600

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

VERSION = "0.7.6"
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

def _is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    return (origin in ALLOWED_ORIGINS) or bool(re.match(VERCEL_REGEX, origin))

# Safety net: always attach CORS headers even on unhandled errors
@app.middleware("http")
async def _ensure_cors_on_all(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception as e:
        import traceback
        print("[ERROR] Unhandled exception in request:", repr(e))
        traceback.print_exc()
        response = PlainTextResponse("Internal Server Error", status_code=500)

    origin = request.headers.get("origin")
    if origin and _is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response

# --- static mounting when running in memory mode ---
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
_try_include(account, "auth-extra")  # guarded include
_try_include(stats, "stats")
_try_include(covers, "covers")

# ---- Auth endpoints: return auth outputs, and set cookie on /login ----
log = logging.getLogger("uvicorn.error")

@app.post("/register")
@app.post("/register/")
def register(body: RegisterIn):
    try:
        return register_user(body)
    except HTTPException as he:
        raise he
    except Exception as e:
        log.exception("register failed")
        raise HTTPException(status_code=400, detail=f"register failed: {type(e).__name__}: {e}")

@app.post("/login")
@app.post("/login/")
def login(body: LoginIn, response: Response):
    try:
        out = login_user(body)  # {"access_token": "..."}
    except HTTPException as he:
        raise he
    except Exception as e:
        log.exception("login failed")
        raise HTTPException(status_code=400, detail=f"login failed: {type(e).__name__}: {e}")

    token = (out or {}).get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="invalid credentials")

    # Set cookie so browser calls (axios/fetch) send it automatically.
    response.set_cookie(
        key="access_token",
        value=token,
        path="/",
        max_age=int(TOKEN_TTL),
        httponly=True,
        secure=True,       # required with SameSite=None
        samesite="none",
    )
    return out

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
