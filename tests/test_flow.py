import io, uuid, pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def make_image_bytes(color=(255, 0, 0), size=(200, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    buf.seek(0)
    return buf

def test_full_flow():
    email = f"{uuid.uuid4()}@example.com"
    password = "Pass123!"
    client.post("/register", json={"email": email, "password": password})

    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/albums/", params={"title": "pytest"}, headers=headers)
    assert r.status_code == 201, r.text
    album_id = r.json()["album_id"]

    files = {"file": ("img.jpg", make_image_bytes(), "image/jpeg")}
    r = client.post("/photos/", params={"album_id": album_id},
                    headers=headers, files=files)
    assert r.status_code == 201, r.text
    assert r.json()["url"].startswith("https://")

    # add 14 more images
    for _ in range(14):
        client.post("/photos/", params={"album_id": album_id},
                    headers=headers, files=files)

    r1 = client.get("/photos/", params={"album_id": album_id, "limit": 10},
                    headers=headers)
    assert r1.status_code == 200, r1.text
    page1 = r1.json()
    assert len(page1["items"]) == 10 and page1["next_key"]

    r2 = client.get("/photos/", params={
        "album_id": album_id,
        "limit": 10,
        "last_key": page1["next_key"]},
        headers=headers)
    assert r2.status_code == 200, r2.text
    page2 = r2.json()
    assert len(page2["items"]) >= 5 and page2["next_key"] is None