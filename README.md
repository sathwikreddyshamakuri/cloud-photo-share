# NuageVault — Private Photo Cloud

NuageVault is a simple, privacy-minded photo app. Create albums, upload photos, open fullscreen, multi-select to download or delete, switch dark mode, verify email, and view a small usage dashboard.

## Features
- Landing page at `/` with **Log in** / **Sign up**
- JWT auth: register, login, logout (logout returns to `/`)
- Albums: create, rename, delete
- Photos: upload, fullscreen viewer, multi-select download/delete
- Dashboard: albums/photos/storage stats
- Profile: avatar, display name, bio, password change
- Dark mode toggle

## Tech Stack
**Frontend:** React + TypeScript + Vite, Tailwind CSS, react-router, react-hot-toast  
**Backend:** FastAPI, AWS DynamoDB (Users/Albums/PhotoMeta), S3 (optional CloudFront)

## MonoRepo Layout
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

##Create app/.env:
