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

