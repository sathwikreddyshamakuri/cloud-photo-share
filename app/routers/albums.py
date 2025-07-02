"""
Album CRUD router (DynamoDB version)
Table name expected:  Albums   (PK: album_id)
"""

import os, time, uuid
import boto3
from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Depends, HTTPException, status
from dotenv import load_dotenv, find_dotenv
from ..auth import decode_token            # adjust if auth.py path differs

# ── AWS & table refs ─────────────────────
load_dotenv(find_dotenv())
REGION = os.getenv("REGION", "us-east-1")

dyna          = boto3.resource("dynamodb", region_name=REGION)
table_albums  = dyna.Table("Albums")

# ── Router ───────────────────────────────
router = APIRouter(prefix="/albums", tags=["albums"])

# Reuse JWT helper from main app
def current_user(token: str = Depends(decode_token)) -> str:
    return token

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_album(title: str, user_id: str = Depends(current_user)):
    album_id = str(uuid.uuid4())
    table_albums.put_item(Item={
        "album_id":   album_id,
        "owner":      user_id,
        "title":      title,
        "created_at": int(time.time()),
    })
    return {"album_id": album_id, "title": title}

@router.get("/")
def list_albums(user_id: str = Depends(current_user)):
    resp = table_albums.scan(FilterExpression=Attr("owner").eq(user_id))
    return {"albums": resp["Items"]}
