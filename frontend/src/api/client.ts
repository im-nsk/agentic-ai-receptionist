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
  sheet_id?: string | null;
  timezone: string;
  client_phone?: string | null;
  business_name?: string | null;
  working_hours: Record<string, unknown>;
  slot_duration?: number | null;
  services?: string[] | null;
  free_text?: string | null;
}

export interface BookingRowResponse {
  row_id: number;
  id: string;
  name: string;
  phone: string;
  date: string;
  time: string;
  status: string;
  created_at: string | null;
  source?: string;
  notes?: string;
}

export interface BookingPatchPayload {
  date?: string;
  time?: string;
  status?: string;
  name?: string;
  phone?: string;
  notes?: string;
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

function coerceSheetRowId(rowId: unknown): number {
  return Math.trunc(typeof rowId === 'number' ? rowId : Number(String(rowId)));
}

export async function getBookings() {
  const { data } = await api.get<BookingRowResponse[]>('/bookings');
  return data
    .map((r) => ({ ...r, row_id: coerceSheetRowId(r.row_id) }))
    .filter((r) => Number.isFinite(r.row_id) && r.row_id >= 2);
}

/** Live metrics from GET /analytics (Google Sheet rows only). */
export interface SheetAnalyticsResponse {
  source: string;
  timezone: string;
  integrations_ready: boolean;
  rows_read_ok: boolean;
  total_bookings: number;
  confirmed_bookings: number;
  cancelled_bookings: number;
  bookings_today: number;
  bookings_this_week: number;
  success_rate_percent: number | null;
  busiest_day: { label: string; count: number } | null;
  last_7_days_labels: string[];
  last_7_days_confirmed_counts: number[];
}

export async function getSheetAnalytics() {
  const { data } = await api.get<SheetAnalyticsResponse>('/analytics');
  return data;
}

export async function patchBooking(rowId: number, payload: BookingPatchPayload) {
  const id = coerceSheetRowId(rowId);
  if (!Number.isFinite(id) || id < 2) {
    throw new Error('Invalid booking row reference');
  }
  const { data } = await api.patch<{ status: string }>(`/bookings/${id}`, payload);
  return data;
}

export async function deleteBooking(rowId: number) {
  const id = coerceSheetRowId(rowId);
  if (!Number.isFinite(id) || id < 2) {
    throw new Error('Invalid booking row reference');
  }
  const { data } = await api.delete<{ status: string }>(`/bookings/${id}`);
  return data;
}

export async function checkAvailability(payload: AppointmentPayload) {
  const { data } = await api.post<AvailabilityResponse>('/check-availability', payload);
  return data;
}

export async function bookAppointment(payload: AppointmentPayload) {
  const { data } = await api.post<BookResponse>('/book', payload);
  return data;
}
