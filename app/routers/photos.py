from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ExifTags
import time, uuid, boto3
from boto3.dynamodb.conditions import Attr

from ..auth import decode_token
from ..aws_config import REGION, S3_BUCKET, dyna
from .albums import table_albums

# -------------------------------------------------------------
router = APIRouter(prefix="/photos", tags=["photos"])
table_photos = dyna.Table("PhotoMeta")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

security = HTTPBearer()

def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(creds.credentials)

# ----------------------- Helper ------------------------------
def extract_exif(fp: Path):
    try:
        img = Image.open(fp)
        width, height = img.size
        exif = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif.items()}
        raw = tag_map.get("DateTimeOriginal")
        taken_at = (
            datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            .replace(tzinfo=timezone.utc).isoformat()
            if raw else None
        )
        return width, height, taken_at
    except Exception:
        return None, None, None

# ----------------------- Upload ------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    album_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # verify album ownership
    resp = table_albums.get_item(Key={"album_id": album_id})
    album = resp.get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(404, "Album not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "file must be an image")

    # save temp file for Pillow
    tmp_path = UPLOAD_DIR / f"tmp-{uuid.uuid4()}"
    with tmp_path.open("wb") as tmp:
        tmp.write(await file.read())

    width, height, taken_at = extract_exif(tmp_path)

    # upload to S3
    photo_id = str(uuid.uuid4())
    s3_key = f"photos/{album_id}/{photo_id}-{file.filename}"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(tmp_path), S3_BUCKET, s3_key,
                   ExtraArgs={"ContentType": file.content_type})
    tmp_path.unlink(missing_ok=True)

    # store metadata
    table_photos.put_item(Item={
        "photo_id":  photo_id,
        "album_id":  album_id,
        "s3_key":    s3_key,
        "uploader":  user_id,
        "width":     width or 0,
        "height":    height or 0,
        "taken_at":  taken_at or "",
        "uploaded_at": int(time.time()),
    })

    url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=3600)

    return {"photo_id": photo_id, "url": url}
