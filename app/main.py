# app/main.py
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos
from .aws_config import dyna, S3_BUCKET, s3   # noqa: F401  (import kept for future use)

app = FastAPI(title="Cloud Photo‑Share API", version="0.6.0")

# ───────────────────────── CORS (TEMPORARY WILDCARD) ─────────────────────────
# While debugging we allow every Origin.  Lock this down to your Vercel URL(s)
# once everything is confirmed working in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # ⚠️  TEMPORARY — use explicit list later
    allow_credentials=True,
    allow_methods=["*"],            # GET, POST, PUT, DELETE, OPTIONS, …
    allow_headers=["*"],
)
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
