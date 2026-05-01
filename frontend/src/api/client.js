import { getToken, logout, isTokenExpired } from "../utils/auth";

const RAW_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "https://agentic-ai-receptionist.onrender.com";
const BASE_URL = RAW_BASE_URL.replace(/\/$/, "");

/**
 * Build request headers.
 * Public routes (login/signup) should not force logout redirects.
 */
function getHeaders(extraHeaders = {}, withAuth = true) {
  const headers = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  if (!withAuth) return headers;

  const token = getToken();

  if (!token) {
    return headers;
  }

  if (isTokenExpired(token)) {
    console.warn("[api] Token expired while preparing request");
    logout();
    return headers;
  }

  return {
    ...headers,
    Authorization: `Bearer ${token}`,
  };
}

async function apiRequest(endpoint, options = {}, config = {}) {
  const { withAuth = true } = config;
  const url = `${BASE_URL}${endpoint}`;

  console.log("[api] Request start", {
    endpoint,
    method: options.method || "GET",
    url,
    withAuth,
  });

  try {
    const res = await fetch(url, {
      ...options,
      headers: getHeaders(options.headers, withAuth),
    });

    console.log("[api] Response status", { endpoint, status: res.status });

    if (res.status === 401) {
      logout();
      throw new Error("unauthorized");
    }

    if (!res.ok) {
      let message = "Something went wrong";

      try {
        const data = await res.json();
        message = data.detail || message;
      } catch {
        message = await res.text();
      }

      throw new Error(message);
    }

    return await res.json();

  } catch (err) {
    console.error("API Error:", err);
    throw err;
  }
}

//
// ========================
// 🔐 AUTH APIs
// ========================
//

export function signup(data) {
  return apiRequest("/signup", {
    method: "POST",
    body: JSON.stringify(data),
  }, { withAuth: false });
}

export function login(data) {
  return apiRequest("/login", {
    method: "POST",
    body: JSON.stringify(data),
  }, { withAuth: false });
}

//
// ========================
// 📊 CLIENT APIs
// ========================
//

export function getClient() {
  return apiRequest("/client");
}

//
export function saveSetup(data) {
  return apiRequest("/setup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

//
// ========================
// 📅 BOOKING APIs
// ========================
//

export function bookAppointment(data) {
  return apiRequest("/book-appointment", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function checkAvailability(data) {
  return apiRequest("/check-availability", {
    method: "POST",
    body: JSON.stringify(data),
  });
}