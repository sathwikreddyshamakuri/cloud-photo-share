// cloud-photo-ui/src/lib/api.ts
import axios from "axios";

/**
 * IMPORTANT:
 * On Vercel, set VITE_API_BASE_URL = https://cloud-photo-share.onrender.com
 * in Project → Settings → Environment Variables, then redeploy.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (window.location.hostname.endsWith(".vercel.app")
    ? "https://cloud-photo-share.onrender.com"
    : "http://localhost:8000");

const api = axios.create({
  baseURL: API_BASE_URL.replace(/\/+$/, ""),
  withCredentials: true, // send/receive cookies cross-site
});

// Keep token support if you also use bearer auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
