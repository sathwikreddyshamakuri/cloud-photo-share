"""
Album CRUD router (DynamoDB)
Table: Albums   (PK = album_id)
"""

import os, time, uuid
import boto3
from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv, find_dotenv

from ..auth import decode_token

# ── AWS setup ────────────────────────────────────────────────
load_dotenv(find_dotenv())
REGION = os.getenv("REGION", "us-east-1")

dyna = boto3.resource("dynamodb", region_name=REGION)
table_albums = dyna.Table("Albums")

# ── Auth helper ──────────────────────────────────────────────
security = HTTPBearer()

def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "invalid or expired token")

# ── Router ───────────────────────────────────────────────────
router = APIRouter(prefix="/albums", tags=["albums"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_album(title: str, user_id: str = Depends(current_user)):
    album_id = str(uuid.uuid4())
    table_albums.put_item(Item={
        "album_id":   album_id,
        "title":      title,
        "owner":      user_id,
        "created_at": int(time.time()),
    })
    return {"album_id": album_id}

@router.get("/")
def list_albums(user_id: str = Depends(current_user)):
    resp = table_albums.scan(FilterExpression=Attr("owner").eq(user_id))
    return {"albums": resp["Items"]}
