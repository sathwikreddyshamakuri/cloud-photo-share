// cloud-photo-ui/src/lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,    // must match the env key above
  headers: { 'Content-Type': 'application/json' },
});

// send JWT on each request
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers!['Authorization'] = `Bearer ${token}`;
  return cfg;
});

export default api;
