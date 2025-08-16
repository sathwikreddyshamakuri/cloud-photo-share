# NuageVault — Cloud Photo Share

Store, organize, and share your memories — privately.  
NuageVault is a full-stack photo app: **FastAPI** backend + **React (TypeScript, Vite, Tailwind)** frontend. It uses **AWS (S3, DynamoDB, SES)** for storage and email. Recommended deploy: **Render** (API) + **Vercel** (UI).

<p align="center">
  <img src="cloud-photo-ui/src/assets/nuagevault-logo.png" alt="NuageVault" height="72" />
</p>

---

## ✨ Features

- 🔐 Email signup/login (JWT) with optional email verification  
- 📁 Albums: create, rename, delete, search  
- 🖼️ Photos: upload, full-screen lightbox, multi-select **download** & **delete**  
- 🌗 Light/dark theme toggle  
- 📊 Dashboard with usage stats (albums / photos / storage)  
- 👤 Profile: avatar, display name, bio, password change, delete account  
- 🧭 Clean routing: **Landing** (`/`), **Login** (`/login`), **Signup** (`/signup`), **Albums** (`/albums`), **Dashboard** (`/dashboard`), etc.

---

## 🗂 Project structure

cloud-photo-share/
├─ app/ # FastAPI backend
│ ├─ main.py
│ ├─ auth.py
│ ├─ aws_config.py
│ ├─ routers/
│ │ ├─ albums.py
│ │ ├─ photos.py
│ │ ├─ users.py
│ │ ├─ account.py
│ │ └─ stats.py
├─ cloud-photo-ui/ # React + Vite + Tailwind frontend
│ ├─ src/
│ │ ├─ lib/api.ts
│ │ ├─ pages/
│ │ └─ components/
│ └─ public/index.html
└─ tests/ # Pytest API tests


---

## 🧰 Tech

- **Backend:** FastAPI, Python 3.12, boto3, passlib, PyJWT  
- **AWS:** S3 (photos), DynamoDB (Users, Albums, PhotoMeta), SES (emails)  
- **Frontend:** React + TypeScript + Vite + Tailwind  
- **Deploy:** Render (API) & Vercel (UI)

---

## 🚀 Quick start (local)

> Prereqs: Python 3.12+, Node 18+, AWS account (S3, DynamoDB, SES).

### 1) Backend (FastAPI)

```bash
cd app
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt

Create app/.env (or export env vars):

# JWT & CORS
JWT_SECRET=replace-me
JWT_EXPIRE_HOURS=168
# allow localhost UI + Vercel
CORS_ORIGINS=http://localhost:5173,https://*.vercel.app

# AWS
AWS_REGION=us-east-1
S3_BUCKET=your-photo-bucket
DDB_USERS_TABLE=Users
DDB_ALBUMS_TABLE=Albums
DDB_PHOTOS_TABLE=PhotoMeta

# Email (optional if you skip verification)
SES_FROM=you@yourdomain.com
AUTO_VERIFY_USERS=0

DynamoDB tables & index

Users (PK: user_id)

Albums (PK: album_id, attrs: owner, title, created_at, cover_url)

PhotoMeta (PK: photo_id, attrs: album_id, owner, s3_key, size, uploaded_at, url)

GSI on PhotoMeta: album_id-index (Partition Key: album_id)



