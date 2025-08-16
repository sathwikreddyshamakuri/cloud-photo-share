# NuageVault — Cloud Photo Share

Fast, private photo storage & sharing.  
Frontend: **React + TypeScript + Vite + Tailwind** • Backend: **FastAPI** • Storage: **AWS (S3 + DynamoDB + SES)**  
Deploy: **Vercel** (UI) + **Render** (API)

---

## Features
- Email signup/login (JWT) with optional verification
- Albums: create/rename/delete/search
- Photos: upload, full-screen lightbox, **multi-select download/delete**
- Dashboard (usage stats), Profile (name/bio/avatar/password)
- Light/Dark theme

---


---

## Quick Start

### 1) Backend (FastAPI)
```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

JWT_SECRET=replace-me
JWT_EXPIRE_HOURS=168
CORS_ORIGINS=http://localhost:5173,https://*.vercel.app

AWS_REGION=us-east-1
S3_BUCKET=your-photo-bucket
DDB_USERS_TABLE=Users
DDB_ALBUMS_TABLE=Albums
DDB_PHOTOS_TABLE=PhotoMeta

SES_FROM=you@yourdomain.com
AUTO_VERIFY_USERS=0

uvicorn app.main:app --reload --port 8000

cd cloud-photo-ui
npm install
