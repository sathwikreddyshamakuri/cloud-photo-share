from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from boto3.dynamodb.conditions import Attr
import time, uuid

from ..auth import decode_token
from ..aws_config import dyna
# -------------------------------------------------------------

router = APIRouter(prefix="/albums", tags=["albums"])
table_albums = dyna.Table("Albums")

# local HTTPBearer so Swagger shows Authorize ― no import from main.py
security = HTTPBearer()

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(creds.credentials)

# ----------------------- Endpoints ---------------------------

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
