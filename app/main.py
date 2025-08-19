import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the app BEFORE including routers
app = FastAPI(title="Cloud Photo-Share API", version="0.7.1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (now under app/routers)
from app.routers import albums, photos, users, account, stats
try:
    from app.routers import util
    app.include_router(util.router, tags=["util"])
except Exception:
    pass

app.include_router(albums.router,  tags=["albums"])
app.include_router(photos.router,  tags=["photos"])
app.include_router(users.router,   tags=["users"])
app.include_router(account.router, tags=["auth-extra"])
app.include_router(stats.router,   tags=["stats"])

# Auth (adjust path if your auth module lives elsewhere)
try:
    from app.auth import RegisterIn, LoginIn, register_user, login_user  # type: ignore
except Exception:
    # If you don't have auth yet, stub the types to avoid import errors
    from typing import Any
    RegisterIn = LoginIn = Any
    def register_user(_: Any): return {"ok": False, "msg": "auth not wired"}
    def login_user(_: Any):    return {"ok": False, "msg": "auth not wired"}

# Misc endpoints
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
