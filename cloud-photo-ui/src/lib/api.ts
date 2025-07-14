import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8001', // or :8000 if that's where your backend runs
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
