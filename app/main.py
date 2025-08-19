# app/main.py
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1) Create the app BEFORE importing/including routers
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

# 3) Import routers AFTER app exists
#    (make sure these modules exist under app/routers/)
from app.routers import albums, photos, users, account, stats

# util router is optional — only include if you created it
try:
    from app.routers import util
    app.include_router(util.router, tags=["util"])
except Exception:
    pass

# 4) Include routers
app.include_router(albums.router,  tags=["albums"])
app.include_router(photos.router,  tags=["photos"])
app.include_router(users.router,   tags=["users"])
app.include_router(account.router, tags=["auth-extra"])
app.include_router(stats.router,   tags=["stats"])

# 5) Auth models & handlers
# Try to import your real auth code; if it isn't present yet,
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

    def register_user(_: RegisterIn):
        return {"ok": False, "msg": "auth not wired"}

    def login_user(_: LoginIn):
        return {"ok": False, "msg": "auth not wired"}

# 6) Misc endpoints
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
