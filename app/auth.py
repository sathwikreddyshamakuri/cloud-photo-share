import os, jwt
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from dotenv import load_dotenv, find_dotenv

# Load .env so we can read JWT_SECRET
load_dotenv(find_dotenv())

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")   # add to .env
JWT_ALGO   = "HS256"



def hash_pw(plain: str) -> str:
    return bcrypt.hash(plain)

def verify_pw(plain: str, hashed: str) -> bool:
    return bcrypt.verify(plain, hashed)


def create_token(user_id: str, exp_secs: int = 3600) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=exp_secs),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token: str) -> str:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])["sub"]
