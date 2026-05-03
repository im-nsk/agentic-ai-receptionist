export const TOKEN_KEY = 'token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function decodePayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split('.')[1];
    const base64Normalized = base64.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64Normalized)
        .split('')
        .map((c) => `%${(`00${c.charCodeAt(0).toString(16)}`).slice(-2)}`)
        .join('')
    );
    return JSON.parse(jsonPayload) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodePayload(token);
  if (!payload?.exp || typeof payload.exp !== 'number') return true;
  return payload.exp * 1000 < Date.now();
}

export function getClientIdFromToken(): string | null {
  const token = getToken();
  if (!token || isTokenExpired(token)) return null;
  const payload = decodePayload(token);
  const clientId = payload?.client_id;
  return typeof clientId === 'string' ? clientId : null;
}

export function logout() {
  removeToken();
  window.location.replace('/login');
}
