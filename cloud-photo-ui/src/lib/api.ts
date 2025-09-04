import axios from "axios";

const RAW = (import.meta.env.VITE_API_URL || "").toString();
export const API_BASE_URL = RAW.replace(/\/+$/, "") || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, 
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});


if (typeof window !== "undefined") {
  console.log("[api] baseURL:", API_BASE_URL, "withCredentials:", true);
}


api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.message ||
      "Request failed";
    err.message = detail;
    return Promise.reject(err);
  }
);

export default api;
