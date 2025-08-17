# NuageVault — Private Photo Cloud

NuageVault is a simple, privacy-minded photo app. Create albums, upload photos, open fullscreen, multi-select to download/delete, toggle dark mode, verify email, and view a usage dashboard.

## Features
- Landing page at `/` with **Log in** / **Sign up**
- JWT auth (register, login, logout → returns to `/`)
- Albums: create, rename, delete
- Photos: upload, fullscreen viewer, multi-select download/delete
- Dashboard: albums/photos/storage stats
- Profile: avatar, display name, bio, password change
- Dark mode toggle

## Stack
**Frontend:** React + TypeScript + Vite, Tailwind CSS, react-router, react-hot-toast  
**Backend:** FastAPI, AWS DynamoDB (Users/Albums/PhotoMeta), S3 (optional CloudFront)

## Repo Layout
cloud-photo-share/
├─ app/ # FastAPI backend
└─ cloud-photo-ui/ # React (Vite) frontend

---

## Quick Start (Local)

### 1) Backend (FastAPI)
```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

Create app/.env:
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name
DYNAMO_USERS=Users
DYNAMO_ALBUMS=Albums
DYNAMO_PHOTOS=PhotoMeta
JWT_SECRET=please-change-to-a-long-random-string
EMAIL_FROM=noreply@your-domain.com
AUTO_VERIFY_USERS=1   # 1 = skip email verification in dev; use 0 in prod

Run the API:
uvicorn app.main:app --reload --port 8000
