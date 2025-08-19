# app/main.py
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers at the top (fixes E402)
from app.routers import albums, photos, users, account, stats

# util router is optional — import if present, else set to None
try:
    from app.routers import util  # type: ignore
except Exception:
    util = None  # type: ignore

# Auth models & handlers:
# Try to import your real auth code; if it's not present yet,
# define minimal Pydantic models + stub functions so the app runs
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

# 1) Create the FastAPI app BEFORE including routers
app = FastAPI(title="Cloud Photo-Share API", version="0.7.1")

# 2) CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://cloud-photo-share-[A-Za-z0-9\-]+\.vercel\.app",
    allow_origins=["http://localhost:5173"],  # dev UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Include routers
if util:
    app.include_router(util.router, tags=["util"])

app.include_router(albums.router,  tags=["albums"])
app.include_router(photos.router,  tags=["photos"])
app.include_router(users.router,   tags=["users"])
app.include_router(account.router, tags=["auth-extra"])
app.include_router(stats.router,   tags=["stats"])

# 4) Misc endpoints
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
    # placeholder – extend later if you implement a public feed
    return {"photos": []}
