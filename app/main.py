# app/main.py

import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import RegisterIn, LoginIn, register_user, login_user
from .routers import albums, photos
from .aws_config import dyna, S3_BUCKET, s3

app = FastAPI(title="Cloud Photo-Share API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers exactly at /albums/ and /photos/
app.include_router(albums.router, tags=["albums"])
app.include_router(photos.router, tags=["photos"])

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
    # …
    return {"photos": items}
