import { isAxiosError } from 'axios';

function formatDetailPayload(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (!Array.isArray(detail)) return '';
  const parts = detail
    .map((entry) => {
      if (!entry || typeof entry !== 'object') return '';
      const e = entry as { msg?: string; loc?: unknown[] };
      return typeof e.msg === 'string' ? e.msg : '';
    })
    .filter(Boolean);
  return parts.length ? parts.join(' ') : '';
}

export function getApiErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const payload = err.response?.data as { detail?: unknown; message?: string } | undefined;
    const fromDetail = payload?.detail !== undefined ? formatDetailPayload(payload.detail) : '';
    if (fromDetail) return fromDetail;
    if (typeof payload?.message === 'string') return payload.message;
    if (typeof err.message === 'string' && err.message !== 'Network Error') return err.message;
  }
  if (err instanceof Error) return err.message;
  return 'Something went wrong.';
}
