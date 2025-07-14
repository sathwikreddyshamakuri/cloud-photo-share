# File: app/routers/photos.py

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Query,
    HTTPException,
    Depends,
    status,
)
import uuid, time

from boto3.dynamodb.conditions import Key
from ..auth import current_user
from ..aws_config import dyna, s3, S3_BUCKET

router = APIRouter()
table_albums = dyna.Table("Albums")
table_photos = dyna.Table("PhotoMeta")


@router.post("/photos/", status_code=status.HTTP_201_CREATED)
def upload_photo(
    album_id: str = Query(..., description="Album ID to upload into"),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    # 1) Verify album exists & is owned by this user
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

    # 2) Upload file to S3
    ext = file.filename.split(".")[-1]
    s3_key = f"{album_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)

    # 3) Record metadata in DynamoDB
    photo_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "photo_id":    photo_id,
        "album_id":    album_id,
        "s3_key":      s3_key,
        "uploaded_at": now,
    }
    table_photos.put_item(Item=item)

    # 4) Return presigned URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=3600,
    )
    return {**item, "url": url}


@router.get("/photos/")
def list_photos(
    album_id: str = Query(..., description="Album ID to filter by"),
    limit: int = Query(10, gt=0, description="Max # of photos to return"),
    last_key: str | None = Query(None, description="Photo ID to continue from"),
    user_id: str = Depends(current_user),
):
    # 1) Verify album & ownership
    alb = table_albums.get_item(Key={"album_id": album_id}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

    # 2) Scan all photos (with pagination)
    resp = table_photos.scan()
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = table_photos.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))

    # 3) Filter & sort
    photos = [it for it in items if it.get("album_id") == album_id]
    photos.sort(key=lambda it: it["uploaded_at"])

    # 4) Paginate
    start = 0
    if last_key:
        for i, it in enumerate(photos):
            if it["photo_id"] == last_key:
                start = i + 1
                break
    page = photos[start : start + limit]

    # 5) Attach URLs
    for it in page:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )

    next_key = page[-1]["photo_id"] if start + limit < len(photos) else None
    return {"items": page, "next_key": next_key}


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    user_id: str = Depends(current_user),
):
    resp = table_photos.get_item(Key={"photo_id": photo_id})
    photo = resp.get("Item")
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    alb = table_albums.get_item(Key={"album_id": photo["album_id"]}).get("Item")
    if not alb or alb["owner"] != user_id:
        raise HTTPException(status_code=403, detail="Not your photo")

    table_photos.delete_item(Key={"photo_id": photo_id})
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=photo["s3_key"])
    except Exception:
        pass

    r
