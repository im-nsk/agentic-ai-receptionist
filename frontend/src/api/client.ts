import axios from 'axios';
import { getToken, isTokenExpired, logout } from '../utils/auth';

const BASE_URL =
  import.meta.env.VITE_API_URL || 'https://agentic-ai-receptionist.onrender.com';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const token = getToken();

  if (!token) return config;

  if (isTokenExpired(token)) {
    logout();
    return Promise.reject(new Error('Session expired'));
  }

  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      logout();
    }

    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      'Something went wrong';

    return Promise.reject(new Error(message));
  }
);

export default client;