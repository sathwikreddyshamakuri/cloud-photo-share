import os, time, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
import boto3
from dotenv import dotenv_values
from dotenv import load_dotenv, find_dotenv

# ────────────────────────────────────────────────────────────
# Load variables from .env and show quick debug output
# ────────────────────────────────────────────────────────────
print("DEBUG cwd =", Path.cwd())  # current working directory

env_path = find_dotenv()  # search upward for a file named ".env"
print("DEBUG env_path =", env_path, "exists?", Path(env_path).exists())

load_dotenv(env_path, override=True)  # load .env contents
print("DEBUG S3_BUCKET =", os.getenv("S3_BUCKET"))

cfg = dotenv_values(env_path)          # ← parse the file directly
print("DEBUG dotenv_values =", cfg)
# ────────────────────────────────────────────────────────────

REGION    = os.getenv("REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET")    # should be "photo-share-650794551"

# AWS clients
s3   = boto3.client("s3", region_name=REGION)
dyna = boto3.resource("dynamodb", region_name=REGION)
table = dyna.Table("PhotoMeta")       # DynamoDB table you created

# FastAPI setup
app = FastAPI(title="Cloud Photo-Share API", version="0.2.0")

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    # accept only images
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    photo_id = str(uuid.uuid4())
    key      = f"photos/{photo_id}-{file.filename}"

    # upload bytes to S3
    body = await file.read()
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=body,
        ContentType=file.content_type
    )

    # store metadata in DynamoDB
    table.put_item(Item={
        "photo_id":    photo_id,
        "s3_key":      key,
        "uploader":    "demo-user",       # to be replaced in Week 2
        "caption":     "",
        "uploaded_at": int(time.time())
    })

    # generate presigned URL (1 h)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600
    )

    return {"photo_id": photo_id, "url": url}

@app.get("/feed")
def get_feed(limit: int = 20):
    # simple scan (fine for a demo)
    resp  = table.scan()
    items = sorted(resp["Items"], key=lambda x: x["uploaded_at"], reverse=True)[:limit]

    # attach presigned URLs
    for it in items:
        it["url"] = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": it["s3_key"]},
            ExpiresIn=3600
        )
    return {"photos": items}
