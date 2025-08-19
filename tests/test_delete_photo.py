# tests/test_delete_photo.py
import uuid
import time
from fastapi.testclient import TestClient
from app.main import app
from app.aws_config import dyna, s3, S3_BUCKET
from app.auth import current_user

app.dependency_overrides[current_user] = lambda: "u1"
client = TestClient(app)

def _album(album_id="a1", owner="u1"):
    dyna.Table("Albums").put_item(Item={"album_id": album_id, "owner": owner})

def _photo(album_id="a1"):
    pid = str(uuid.uuid4())
    key = f"{album_id}/{pid}.jpg"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=b"x")
    dyna.Table("PhotoMeta").put_item(
        Item={
            "photo_id": pid,
            "album_id": album_id,
            "s3_key": key,
            "uploaded_at": int(time.time()),
        }
    )
    return pid, key

def test_delete_photo_ok():
    _album()
    pid, key = _photo()
    assert client.delete(f"/photos/{pid}").status_code == 204
    assert "Item" not in dyna.Table("PhotoMeta").get_item(Key={"photo_id": pid})
    assert s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=key)["KeyCount"] == 0

def test_delete_photo_forbidden():
    _album(owner="u2")
    pid, _ = _photo()
    assert client.delete(f"/photos/{pid}").status_code == 403
