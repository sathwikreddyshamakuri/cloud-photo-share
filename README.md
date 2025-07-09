# Cloud-Photo-Share

> A lightweight, JWT-secured REST API for uploading, managing, and sharing photos in the cloud.
+ ![CI](https://img.shields.io/github/actions/workflow/status/sathwikreddyshamakuri/cloud-photo-share/ci.yml?branch=main)

---

## Table of Contents
1. [Overview](#overview)  
2. [Features](#features)  
3. [Tech Stack](#tech-stack)  
4. [Quick Start](#quick-start)  
5. [Configuration](#configuration)  
6. [Running Locally](#running-locally)  
7. [API Reference](#api-reference)  
8. [Development Workflow](#development-workflow)  
9. [Contributing](#contributing)  
10. [License](#license)

---

## Overview
Cloud-Photo-Share lets you and your friends upload photos to a secure cloud bucket, organize them into albums, and share public or private links—all via a clean JSON REST API. Authentication is handled with JSON Web Tokens (JWT) so every request is stateless and easy to scale.

## Features
- **User accounts & JWT auth** (`/register`, `/login`)
- **Photo upload & EXIF extraction** (dimensions, taken-at date)
- **Album CRUD** (create & list today, easy to extend to rename/delete)
- **Signed share links** that auto-expire
- **Pagination & thumbnails** for large libraries
- **Continuous Integration** with GitHub Actions

## Tech Stack
| Layer               | Choices |
|---------------------|---------|
| **Language**        | Python 3.12 |
| **Web Framework**   | FastAPI + Uvicorn |
| **Auth**            | PyJWT, Passlib (bcrypt) |
| **Database**        | **DynamoDB** |
| **Object Storage**  | AWS S3 |
| **Testing**         | Pytest |

## Quick Start
```bash
# 1. Clone & enter
git clone https://github.com/your-handle/cloud-photo-share.git
cd cloud-photo-share

# 2. Create virtual env
python -m venv .venv && source .venv/Activate   # Linux / macOS
#   or
.\.venv\Scripts\Activate                        # Windows PowerShell

# 3. Install deps
pip install -r requirements.txt

# 4. Start API server  (needs AWS creds + .env in place)
uvicorn app.main:app --reload
