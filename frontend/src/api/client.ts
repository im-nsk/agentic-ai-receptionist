import axios from 'axios';
import { getToken, isTokenExpired, logout } from '@/utils/auth';

const envUrl = import.meta.env.VITE_API_URL;
const BASE_URL =
  (typeof envUrl === 'string' ? envUrl : '').replace(/\/$/, '') ||
  (import.meta.env.DEV ? 'http://localhost:10000' : '');

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  if (config.skipAuth) return config;

  const token = getToken();
  if (!token) return config;

  if (isTokenExpired(token)) {
    logout();
    return Promise.reject(new Error('Session expired'));
  }

  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const skipAuth = (err.config as { skipAuth?: boolean } | undefined)?.skipAuth === true;
    if (err.response?.status === 401 && !skipAuth) {
      logout();
    }

    return Promise.reject(err);
  }
);

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

export interface VerifyOtpPayload {
  email: string;
  code: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
}

export interface ClientResponse {
  name: string;
  minutes_used: number;
  plan_limit: number;
  calendar_id: string;
  sheet_id: string;
  timezone: string;
  phone_number: string;
  client_phone: string;
  setup_complete: boolean;
  business_name: string;
  working_hours: Record<string, unknown> | string | null;
  slot_duration: number;
  services: string[];
  free_text: string;
}

export interface SetupPayload {
  calendar_id: string;
  sheet_id: string;
  timezone: string;
  client_phone?: string | null;
  business_name?: string | null;
  working_hours: Record<string, unknown>;
  slot_duration?: number | null;
  services?: string[] | null;
  free_text?: string | null;
}

export interface BookingRowResponse {
  id: string;
  name: string;
  phone: string;
  date: string;
  time: string;
  status: string;
  created_at: string | null;
}

export interface AppointmentPayload {
  client_id: string;
  name: string;
  phone: string;
  date: string;
  time: string;
}

export interface AvailabilityResponse {
  available: boolean;
  message: string;
}

export interface BookResponse {
  status: string;
  message?: string;
}

export async function signup(payload: SignupPayload) {
  const { data } = await api.post<{ status: string; email?: string }>('/signup', payload, { skipAuth: true });
  return data;
}

export interface EmailPayload {
  email: string;
}

export interface ResetPasswordPayload {
  email: string;
  code: string;
  new_password: string;
}

export async function resendSignupOtp(payload: EmailPayload) {
  const { data } = await api.post<{ status: string }>('/resend-otp', payload, { skipAuth: true });
  return data;
}

export async function forgotPassword(payload: EmailPayload) {
  const { data } = await api.post<{ status: string }>('/forgot-password', payload, { skipAuth: true });
  return data;
}

export async function resetPassword(payload: ResetPasswordPayload) {
  const { data } = await api.post<{ status: string }>('/reset-password', payload, { skipAuth: true });
  return data;
}

export async function verifyOtp(payload: VerifyOtpPayload) {
  const { data } = await api.post<LoginResponse>('/verify-otp', payload, { skipAuth: true });
  return data;
}

export async function login(payload: LoginPayload) {
  const { data } = await api.post<LoginResponse>('/login', payload, { skipAuth: true });
  return data;
}

export async function getClient() {
  const { data } = await api.get<ClientResponse>('/client');
  return data;
}

export async function postSetup(payload: SetupPayload) {
  const { data } = await api.post<{ status: string }>('/setup', payload);
  return data;
}

export async function getBookings() {
  const { data } = await api.get<BookingRowResponse[]>('/bookings');
  return data;
}

export async function checkAvailability(payload: AppointmentPayload) {
  const { data } = await api.post<AvailabilityResponse>('/check-availability', payload);
  return data;
}

export async function bookAppointment(payload: AppointmentPayload) {
  const { data } = await api.post<BookResponse>('/book-appointment', payload);
  return data;
}
