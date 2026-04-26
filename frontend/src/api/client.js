/**
 * client.js
 *
 * Central API layer
 * - Handles auth
 * - Handles errors
 * - Auto logout on 401
 */
/**
 * client.js (FINAL Production Safe)
 */

import { getToken, logout, isTokenExpired } from "../utils/auth";

const BASE_URL =
  import.meta.env.VITE_API_URL ||
  "https://agentic-ai-receptionist.onrender.com";

/**
 * 🔐 Build headers safely
 */
function getAuthHeaders(extraHeaders = {}) {
  const token = getToken();

  // ✅ Fix: logout immediately if token invalid
  if (!token || isTokenExpired(token)) {
    logout();
    return {
      "Content-Type": "application/json",
      ...extraHeaders,
    };
  }

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...extraHeaders,
  };
}

/**
 * 🌐 Core API handler
 */
async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: getAuthHeaders(options.headers),
    });

    // 🔥 Auto logout if unauthorized
    if (res.status === 401) {
      logout();
      throw new Error("unauthorized");
    }

    // ❌ Handle server errors properly
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
  });
}

export function login(data) {
  return apiRequest("/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
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
// ========================
// ⚙️ SETUP API (🔥 YOU MISSED THIS BEFORE)
// ========================
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