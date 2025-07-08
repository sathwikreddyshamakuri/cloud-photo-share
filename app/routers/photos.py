# app/routers/photos.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ExifTags
import time, uuid, json, boto3
from boto3.dynamodb.conditions import Attr, Key

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# ── router & AWS tables ───────────────────────────────────────
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")

# ── auth helper (local) ───────────────────────────────────────
security = HTTPBearer()

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(creds.credentials)

# ── temp folder for EXIF work ─────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ── EXIF helper ───────────────────────────────────────────────
def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        width, height = img.size
        exif = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif.items()}
        raw = tag_map.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if raw else None
        )
        return width, height, taken_at
    except Exception:
        return None, None, None

# ---------- Upload photo + thumbnail ----------
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    #  verify album ownership
    resp_album = table_albums.get_item(Key={"album_id": album_id})
    album = resp_album.get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    #  save temp file
    tmp_path = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp_path.open("wb") as tmp:
        tmp.write(await file.read())

    width, height, taken_at = extract_exif(tmp_path)

    #  create 128-px thumbnail
    thumb_path = UPLOAD_DIR / f"thumb-{uuid.uuid4()}.jpg"
    with Image.open(tmp_path) as img:
        img.thumbnail((128, 128))
        img.convert("RGB").save(thumb_path, "JPEG", quality=85)

    #  upload originals + thumb to S3
    photo_id = str(uuid.uuid4())
    s3_key    = f"photos/{album_id}/{photo_id}-{file.filename}"
    thumb_key = f"thumbs/{album_id}/{photo_id}.jpg"
    s3 = boto3.client("s3", region_name=REGION)

    s3.upload_file(str(tmp_path),  S3_BUCKET, s3_key,
                   ExtraArgs={"ContentType": file.content_type})
    s3.upload_file(str(thumb_path), S3_BUCKET, thumb_key,
                   ExtraArgs={"ContentType": "image/jpeg"})

    tmp_path.unlink(missing_ok=True)
    thumb_path.unlink(missing_ok=True)

    #  metadata
    table_photos.put_item(Item={
        "photo_id":  photo_id,
        "album_id":  album_id,
        "s3_key":    s3_key,
        "thumb_key": thumb_key,
        "uploader":  user_id,
        "width":     width or 0,
        "height":    height or 0,
        "taken_at":  taken_at or "",
        "uploaded_at": int(time.time()),
    })

    url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600)
    thumb_url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": thumb_key}, ExpiresIn=3600)

    return {"photo_id": photo_id, "url": url, "thumb_url": thumb_url}
