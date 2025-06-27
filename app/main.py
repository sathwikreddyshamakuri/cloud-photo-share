from fastapi import FastAPI, UploadFile, File
import uuid, time

app = FastAPI(title="Cloud Photo-Share API", version="0.1.0")

# Temporary in-memory list until we wire S3/DynamoDB
photo_meta = []

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    photo_id = str(uuid.uuid4())
    # TODO: S3 upload in Week 1
    photo_meta.append({
        "photo_id": photo_id,
        "filename": file.filename,
        "uploaded_at": time.time()
    })
    return {"photo_id": photo_id}

@app.get("/feed")
def get_feed():
    # Newest first
    return {"photos": list(reversed(photo_meta))}
