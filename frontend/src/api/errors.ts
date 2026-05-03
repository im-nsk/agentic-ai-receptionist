import { isAxiosError } from 'axios';

export function getApiErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const payload = err.response?.data as { detail?: string; message?: string } | undefined;
    if (typeof payload?.detail === 'string') return payload.detail;
    if (typeof payload?.message === 'string') return payload.message;
    if (typeof err.message === 'string' && err.message !== 'Network Error') return err.message;
  }
  if (err instanceof Error) return err.message;
  return 'Something went wrong.';
}
