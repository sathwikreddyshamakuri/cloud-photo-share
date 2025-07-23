# app/main.py
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos, users, account  # make sure these files exist
from .aws_config import dyna, S3_BUCKET, s3  # noqa: F401  keep imports for side‑effects

app = FastAPI(title="Cloud Photo‑Share API", version="0.7.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(albums.router,  tags=["albums"])
app.include_router(photos.router,  tags=["photos"])
app.include_router(users.router,   tags=["users"])
app.include_router(account.router, tags=["auth-extra"])

# Health/check
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
