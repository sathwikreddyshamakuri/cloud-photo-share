// cloud-photo-ui/src/lib/api.ts
import axios from "axios";

const RAW = (import.meta.env.VITE_API_URL || "").toString();
export const API_BASE_URL = RAW.replace(/\/+$/, "") || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { Accept: "application/json" }, // don't force JSON content-type globally
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

export function setAuthToken(token?: string) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
  applyAuthHeader();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("token-change"));
  }
}

applyAuthHeader();

// Auto-choose Content-Type: JSON only for plain objects; leave FormData/Blob/File alone.
api.interceptors.request.use((config) => {
  const headers: any = config.headers as any;

  // Respect caller-provided content-type if set
  const hasCT =
    (headers?.get && (headers.has("Content-Type") || headers.has("content-type"))) ||
    (!!headers && (headers["Content-Type"] || headers["content-type"]));

  if (!hasCT) {
    const d = config.data;
    const isFormData = typeof FormData !== "undefined" && d instanceof FormData;
    const isBlob = typeof Blob !== "undefined" && d instanceof Blob;
    const isFile = typeof File !== "undefined" && d instanceof File;
    const isPlainObject =
      d &&
      typeof d === "object" &&
      !isFormData &&
      !isBlob &&
      !isFile &&
      !Array.isArray(d);

    if (isPlainObject) {
      if (headers?.set) headers.set("Content-Type", "application/json");
      else (config.headers as any)["Content-Type"] = "application/json";
    }
  }
  return config;
});

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
