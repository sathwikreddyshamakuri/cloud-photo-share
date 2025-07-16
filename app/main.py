# app/main.py
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos
from .aws_config import dyna, S3_BUCKET, s3    # noqa: F401  (kept for future)

app = FastAPI(title="Cloud Photo‑Share API", version="0.6.0")

# ────────────────────────  CORS  ────────────────────────
# The browser sends an OPTIONS pre‑flight before every POST/PUT/DELETE
# from your Vercel frontend.  We must answer it, otherwise the real
# request is never sent and you see “405 Method Not Allowed”.
ALLOWED_ORIGINS = [
    # Production Vercel URL(s) ─ edit to match yours
    "https://cloud-photo-share-y61e-9a65swvd2.vercel.app",
    # Preview / branch deploys (optional but handy)
    "https://cloud-photo-share-git-main-sathwik-reddys-projects-fad3056d.vercel.app",
    # Local Vite dev server
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # use ["*"] only while debugging
    allow_credentials=True,
    allow_methods=["*"],             # GET,POST,PUT,DELETE,OPTIONS…
    allow_headers=["*"],
)
# ─────────────────────────────────────────────────────────

# Mount routers
app.include_router(albums.router, tags=["albums"])
app.include_router(photos.router, tags=["photos"])

# ────────────────────────  End‑points  ────────────────────────
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
    # placeholder – implement later
    return {"photos": []}
