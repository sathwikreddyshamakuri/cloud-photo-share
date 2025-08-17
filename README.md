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
```text
cloud-photo-share/
├─ app/              # FastAPI backend
└─ cloud-photo-ui/   # React (Vite) frontend
