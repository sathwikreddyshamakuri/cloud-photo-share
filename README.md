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
```
## Quick Start(Local)
## Backend(FastAPI)
```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
## Create app/.env:
```bash
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name
DYNAMO_USERS=Users
DYNAMO_ALBUMS=Albums
DYNAMO_PHOTOS=PhotoMeta
JWT_SECRET=please-change-to-a-long-random-string
EMAIL_FROM=noreply@your-domain.com
AUTO_VERIFY_USERS=1
```
## Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```
## 2) Frontend (Vite)
```bash
cd cloud-photo-ui
npm install
```
## Create cloud-photo-ui/.env.local:
```bash
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=NuageVault
```
## Start dev server:
```bash
npm run dev
```
## 🧭 Frontend routes
``` text
/ — Landing page (marketing + “Get started” / “Log in” buttons)

/login — Login screen (success banner + toast when redirected from signup)

/signup — Registration form

/albums — Main app (album list)

/albums/:id — Album detail (upload, select, download, delete, lightbox)

/dashboard — Usage stats

/profile — Profile & account

/forgot, /reset, /verify — Password reset & email verification flows
```
## 🔐 Security & privacy
```text
JWT stored in localStorage

S3 object URLs should be signed if you require stricter privacy (current code assumes safe distribution; you can switch to S3 pre-signed URLs/CloudFront signed cookies easily).

SES sandbox requires verified emails; set AUTO_VERIFY_USERS=1 during development if you prefer to skip email verification (not recommended for prod).
```
## 🛠 Troubleshooting
```text
Landing vs Login loop
If / shows login instead of landing, ensure router guards only redirect when a valid token exists, and your logout navigates to / after removing the token.

Stats shows “Failed to load stats”
Confirm GET /stats/ exists and frontend calls /stats/ (not /users/me/stats). Also ensure PhotoMeta has GSI album_id-index.

CORS 401/403
Add your Vercel domain to CORS allow list. Double-check Authorization: Bearer <token> in requests.

DynamoDB scans slow / expensive
Use queries on GSIs (album_id-index). Avoid full table scans in hot paths
```
## Appendix — minimal IAM policy (example)
```bash
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject"], "Resource": "arn:aws:s3:::your-photo-bucket/*" },
    { "Effect": "Allow", "Action": ["dynamodb:*"], "Resource": [
      "arn:aws:dynamodb:REGION:ACCOUNT:table/Users",
      "arn:aws:dynamodb:REGION:ACCOUNT:table/Albums",
      "arn:aws:dynamodb:REGION:ACCOUNT:table/PhotoMeta",
      "arn:aws:dynamodb:REGION:ACCOUNT:table/PhotoMeta/index/album_id-index"
    ]},
    { "Effect": "Allow", "Action": ["ses:SendEmail","ses:SendRawEmail"], "Resource": "*" }
  ]
}
```


