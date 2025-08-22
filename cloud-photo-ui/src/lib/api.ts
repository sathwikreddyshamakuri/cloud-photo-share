// cloud-photo-ui/src/lib/api.ts
import axios from "axios";

/**
 * Use env var in prod; fall back sensibly in dev.
 * IMPORTANT: On Vercel you must set VITE_API_BASE_URL in Project → Settings → Environment Variables
 * and redeploy, because Vite inlines env vars at build time.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (window.location.hostname.endsWith(".vercel.app")
    ? "https://cloud-photo-share.onrender.com"
    : "http://localhost:8000");

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // send/receive cookies cross-site
});

// Optional: keep bearer-token auth working in parallel with cookies
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
