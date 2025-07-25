# app/auth.py
import time
import uuid
import os
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from boto3.dynamodb.conditions import Attr

from .aws_config import dyna
from .emailer import send_email

AUTO_VERIFY = os.getenv("AUTO_VERIFY_USERS", "0") == "1"

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM  = "HS256"
TOKEN_TTL  = 60 * 60  # 1 hour

pwd_ctx  = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

table_users  = dyna.Table("Users")
table_tokens = dyna.Table("Tokens")

def hash_pw(p: str) -> str:
    return pwd_ctx.hash(p)

def verify_pw(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)

def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + TOKEN_TTL}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")

def new_one_time_token(user_id: str, kind: str, ttl_seconds: int = 3600) -> str:
    tok = str(uuid.uuid4())
    expires = int(time.time()) + ttl_seconds
    table_tokens.put_item(Item={
        "token": tok,
        "type": kind,
        "user_id": user_id,
        "expires_at": expires,
    })
    return tok

def consume_token(token: str, kind: str) -> str:
    resp = table_tokens.get_item(Key={"token": token})
    item = resp.get("Item")
    if not item or item.get("type") != kind or item.get("expires_at", 0) < time.time():
        raise HTTPException(400, "Invalid or expired token")
    table_tokens.delete_item(Key={"token": token})
    return item["user_id"]

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    new_password: str

class VerifyIn(BaseModel):
    token: str

class ChangePwdIn(BaseModel):
    current_password: str
    new_password: str

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(creds.credentials)

def register_user(body: RegisterIn):
    # prevent duplicate email
    if table_users.scan(FilterExpression=Attr("email").eq(body.email))["Items"]:
        raise HTTPException(400, "email already registered")

    user_id = str(uuid.uuid4())
    item = {
        "user_id":        user_id,
        "email":          body.email,
        "password_hash":  hash_pw(body.password),
        "email_verified": AUTO_VERIFY,
    }
    table_users.put_item(Item=item)

    email_sent = False
    if not AUTO_VERIFY:
        token = new_one_time_token(user_id, "verify", 24 * 3600)
        verify_link = f"{os.getenv('PUBLIC_UI_URL', '')}/verify?token={token}"
        try:
            send_email(
                to=body.email,
                subject="Verify your email",
                html=f"<p>Click to verify: <a href='{verify_link}'>{verify_link}</a></p>",
                text=f"Verify: {verify_link}",
            )
            email_sent = True
        except Exception as e:
            # Log error but don't block account creation
            print("EMAIL ERROR:", e)

    return {
        "user_id":     user_id,
        "email_sent":  email_sent,
        "need_verify": not AUTO_VERIFY,
    }

def login_user(body: LoginIn):
    resp = table_users.scan(FilterExpression=Attr("email").eq(body.email))
    if not resp["Items"]:
        raise HTTPException(401, "user not found")

    user = resp["Items"][0]

    if not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "bad credentials")

    if not AUTO_VERIFY and not user.get("email_verified", False):
        raise HTTPException(403, "email not verified")

    return {"access_token": create_token(user["user_id"])}

def change_password(user_id: str, data: ChangePwdIn):
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item or not verify_pw(data.current_password, item["password_hash"]):
        raise HTTPException(401, "wrong password")
    item["password_hash"] = hash_pw(data.new_password)
    table_users.put_item(Item=item)
    return {"msg": "changed"}

def forgot_password(body: ForgotIn):
    resp = table_users.scan(FilterExpression=Attr("email").eq(body.email))
    if resp["Items"]:
        user = resp["Items"][0]
        tok = new_one_time_token(user["user_id"], "reset", 3600)
        reset_url = f"{os.getenv('PUBLIC_UI_URL', '')}/reset?token={tok}"
        send_email(
            to=body.email,
            subject="Reset your password",
            html=f"<p>Reset link (1h): <a href='{reset_url}'>{reset_url}</a></p>",
            text=f"Reset: {reset_url}",
        )
    return {"msg": "If that email exists, a link was sent."}

def reset_password(body: ResetIn):
    user_id = consume_token(body.token, "reset")
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "user not found")
    item["password_hash"] = hash_pw(body.new_password)
    table_users.put_item(Item=item)
    return {"msg": "password updated"}

def verify_email(body: VerifyIn):
    user_id = consume_token(body.token, "verify")
    item = table_users.get_item(Key={"user_id": user_id}).get("Item")
    if not item:
        raise HTTPException(404, "user not found")
    item["email_verified"] = True
    table_users.put_item(Item=item)
    return {"msg": "verified"}
