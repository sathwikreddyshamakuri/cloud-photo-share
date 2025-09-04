// cloud-photo-ui/src/lib/api.ts
import axios from "axios";

const RAW = (import.meta.env.VITE_API_URL || "").toString();
export const API_BASE_URL = RAW.replace(/\/+$/, "") || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // send cookies if browser allows
  headers: { "Content-Type": "application/json", Accept: "application/json" },
});

const TOKEN_KEY = "token";

// apply/remove Authorization header from localStorage
function applyAuthHeader() {
  const t =
    typeof window !== "undefined" ? window.localStorage.getItem(TOKEN_KEY) : null;
  if (t) {
    api.defaults.headers.common["Authorization"] = `Bearer ${t}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

// allow pages to set/clear token centrally
export function setAuthToken(token?: string) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
  applyAuthHeader();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("token-change"));
  }
}

applyAuthHeader();

// auto-clear on 401 so we don’t loop
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) setAuthToken(undefined);
    return Promise.reject(err);
  }
);

if (typeof window !== "undefined") {
  console.log(
    "[api] baseURL:",
    API_BASE_URL,
    "withCredentials:",
    true,
    "auth header:",
    !!api.defaults.headers.common["Authorization"]
  );
}

export default api;
