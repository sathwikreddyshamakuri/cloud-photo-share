![CI](https://github.com/sathwikreddyshamakuri/cloud-photo-share/actions/workflows/ci.yml/badge.svg)

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

### Repo Layout
```
cloud-photo-share/
├─ app/              # FastAPI backend
└─ cloud-photo-ui/   # React (Vite) frontend
```

## Quick Start (Local)

### 1. Backend (FastAPI)
```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Create app/.env:
```env
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name
DYNAMO_USERS=Users
DYNAMO_ALBUMS=Albums
DYNAMO_PHOTOS=PhotoMeta
JWT_SECRET=your-random-secret-key-here
EMAIL_FROM=noreply@nuagevault.com
AUTO_VERIFY_USERS=1
RESEND_API_KEY=your-resend-api-key-here
```

### Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Vite)
```bash
cd cloud-photo-ui
npm install
```

### Create cloud-photo-ui/.env.local:
```env
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=NuageVault
```

### Start dev server:
```bash
npm run dev
```

## 🧭 Frontend Routes

| Route | Description |
|---|---|
| `/` | Landing page (marketing + Get started / Log in) |
| `/login` | Login screen |
| `/signup` | Registration form |
| `/albums` | Main app (album list) |
| `/albums/:id` | Album detail (upload, select, download, delete, lightbox) |
| `/dashboard` | Usage stats |
| `/profile` | Profile & account |
| `/forgot` | Forgot password |
| `/reset` | Reset password |
| `/verify` | Email verification |

## 🏗 Architecture

```
Vercel (React frontend)
        ↓
Render (FastAPI backend)
        ↓
AWS DynamoDB (Users / Albums / PhotoMeta / Tokens)
AWS S3 (photo file storage)
Resend (email verification & password reset)
```

## 🔐 Security & Privacy

- JWT tokens are issued as HttpOnly cookies on login (inaccessible to JavaScript). 
  The frontend also sends an Authorization header for compatibility. 
  HttpOnly cookies are the primary security mechanism.
- All S3 photo URLs are pre-signed with a 1-hour expiry, ensuring only authenticated users can access photos. URLs cannot be shared or accessed without a valid signed request.
- RESEND sandbox requires verified emails. Set `AUTO_VERIFY_USERS=1` during development to skip email verification (not recommended for production).

## 🛠 Troubleshooting

**Landing vs Login loop:**
Ensure router guards only redirect when a valid token exists, and logout navigates to `/` after removing the token.

**Stats shows "Failed to load stats":**
Confirm `GET /stats/` exists and frontend calls `/stats/` (not `/users/me/stats`). Also ensure PhotoMeta has GSI `album_id-index`.

**CORS 401/403:**
Add Vercel domain to CORS allow list. Double-check `Authorization: Bearer <token>` in requests.

**DynamoDB scans slow / expensive:**
Use queries on GSIs (`album_id-index`). Avoid full table scans in hot paths.

## 📋 Appendix — Minimal IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-photo-bucket/*"
    },
    {
      "Sid": "UsersTableRW",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/Users"
    },
    {
      "Sid": "UsersEmailIndex",
      "Effect": "Allow",
      "Action": ["dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/Users/index/email-index"
    },
    {
      "Sid": "AlbumsTableRW",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/Albums"
    },
    {
      "Sid": "PhotoMetaTableRW",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/PhotoMeta"
    },
    {
      "Sid": "PhotoMetaAlbumIndex",
      "Effect": "Allow",
      "Action": ["dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/PhotoMeta/index/album_id-index"
    },
    {
      "Sid": "TokensTableRW",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/Tokens"
    }
  ]
}
```
