# app/auth.py
import time
import uuid
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt

from .aws_config import dyna
from boto3.dynamodb.conditions import Attr


# ── Configuration ────────────────────────────────────────────────
SECRET_KEY = "your-secret-key"   # ❗ replace with your real secret
ALGORITHM  = "HS256"
pwd_ctx    = CryptContext(schemes=["bcrypt"], deprecated="auto")
security   = HTTPBearer()


# ── Helpers ──────────────────────────────────────────────────────
def hash_pw(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_pw(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + 3600}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Pydantic models ──────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str


# ── Dependency to grab the current user ──────────────────────────
def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    return decode_token(creds.credentials)


# ── Registration & login logic ──────────────────────────────────
def register_user(body: RegisterIn):
    table = dyna.Table("Users")

    # uniqueness check
    if table.scan(FilterExpression=Attr("email").eq(body.email))["Items"]:
        raise HTTPException(status_code=400, detail="email already registered")

    user_id = str(uuid.uuid4())
    table.put_item(
        Item={
            "user_id":       user_id,
            "email":         body.email,
            "password_hash": hash_pw(body.password),

            # new profile defaults
            "display_name": body.email.split("@")[0],
            "bio":          "",
            "avatar_key":   None,
        }
    )
    return {"user_id": user_id}


def login_user(body: LoginIn):
    table = dyna.Table("Users")
    resp = table.scan(FilterExpression=Attr("email").eq(body.email))
    if not resp["Items"]:
        raise HTTPException(status_code=401, detail="user not found")

    user = resp["Items"][0]
    if not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="bad credentials")

    return {"access_token": create_token(user["user_id"])}
