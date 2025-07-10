# app/routers/photos.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ExifTags
import time, uuid, os, boto3
from boto3.dynamodb.conditions import Attr

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna  
from .albums import table_albums                  # reuse Albums table

router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")
UPLOAD_DIR = Path("uploads")              # temp folder for PIL
UPLOAD_DIR.mkdir(exist_ok=True)

def current_user(token: str = Depends(decode_token)) -> str:
    return token

def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        width, height = img.size
        exif = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif.items()}
        taken_raw = tag_map.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(taken_raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
            if taken_raw else None
        )
        return width, height, taken_at
    except Exception:
        return None, None, None

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # 1. verify album belongs to user
    resp = table_albums.get_item(Key={"album_id": album_id})
    album = resp.get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    # 2. basic type check
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # 3. write temp file for Pillow
    temp_path = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with temp_path.open("wb") as tmp:
        tmp.write(await file.read())

    width, height, taken_at = extract_exif(temp_path)

    # 4. upload to S3
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(temp_path), S3_BUCKET, s3_key,
                   ExtraArgs={"ContentType": file.content_type})
    temp_path.unlink(missing_ok=True)

    # 5. store metadata
    table_photos.put_item(Item={
        "photo_id":  photo_id,
        "album_id":  album_id,
        "s3_key":    s3_key,
        "uploader":  user_id,
        "width":     width or 0,
        "height":    height or 0,
        "taken_at":  taken_at or "",
        "uploaded_at": int(time.time())
    })

    url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=3600)

    return {"photo_id": photo_id, "url": url}
