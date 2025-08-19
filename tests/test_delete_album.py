# tests/test_delete_album.py
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

def test_delete_album_ok():
    _album()
    _photo()
    assert client.delete("/albums/a1").status_code == 204
    # album row gone
    assert "Item" not in dyna.Table("Albums").get_item(Key={"album_id": "a1"})
    # photos gone
    resp = dyna.Table("PhotoMeta").query(
        IndexName="album_id-index",
        KeyConditionExpression="album_id = :a",
        ExpressionAttributeValues={":a": "a1"},
    )
    assert resp.get("Count", 0) == 0

def test_delete_album_forbidden():
    _album(owner="u2")
    assert client.delete("/albums/a1").status_code == 404
