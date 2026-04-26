/**
 * auth.js (FINAL Production Safe)
 */

const TOKEN_KEY = "token";

/**
 * 🔐 Get token
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * 🔐 Set token
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * 🚪 Logout
 */
export function logout() {
  localStorage.removeItem(TOKEN_KEY);

  // Force app reset (safe for now)
  window.location.replace("/");
}

/**
 * 🔍 Decode JWT safely (base64url support)
 */
function decodePayload(token) {
  try {
    const base64 = token.split(".")[1];

    // Convert base64url → base64
    const base64Normalized = base64
      .replace(/-/g, "+")
      .replace(/_/g, "/");

    const jsonPayload = decodeURIComponent(
      atob(base64Normalized)
        .split("")
        .map((c) =>
          "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)
        )
        .join("")
    );

    return JSON.parse(jsonPayload);

  } catch {
    return null;
  }
}

/**
 * ⏳ Check expiry
 */
export function isTokenExpired(token) {
  const payload = decodePayload(token);

  if (!payload || !payload.exp) return true;

  return payload.exp * 1000 < Date.now();
}