# ---------- List photos in an album (paginated) ----------
import json
from boto3.dynamodb.conditions import Key          # ADD this with other imports

@router.get("/", tags=["photos"])
def list_photos(
    album_id: str,
    limit: int = 20,
    last_key: str | None = None,
    user_id: str = Depends(current_user),
):
    """Return up to <limit> photos in one album, newest first.
    Pass ?last_key=<value-from-previous-response> for the next page.
    """

    # 1️⃣ ensure the caller owns the album
    resp_album = table_albums.get_item(Key={"album_id": album_id})
    album = resp_album.get("Item")
    if not album or album["owner"] != user_id:
        raise HTTPException(status_code=404, detail="Album not found")

    # 2️⃣ query the GSI (album_id-index) instead of a full table scan
    kwargs = {
        "IndexName": "album_id-index",
        "KeyConditionExpression": Key("album_id").eq(album_id),
        "ScanIndexForward": False,   # newest → oldest
        "Limit": limit,
    }
    if last_key:
        kwargs["ExclusiveStartKey"] = json.loads(last_key)

    resp = table_photos.query(**kwargs)
    items = resp["Items"]

    # 3️⃣ presign URLs so the images can be displayed immediately
    s3 = boto3.client("s3", region_name=REGION)
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600,
        )

    return {
        "items": items,
        "next_key": json.dumps(resp["LastEvaluatedKey"])
        if "LastEvaluatedKey" in resp
        else None,
    }
