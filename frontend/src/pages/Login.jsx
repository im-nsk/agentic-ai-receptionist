/**
 * Login.jsx (Production Ready - Final)
 *
 * - JWT auth (centralized)
 * - Auto redirect (safe)
 * - Prevent duplicate requests
 * - Enter key support
 * - Better validation + UX
 */

/**
 * Login.jsx (FINAL Production Safe)
 */

import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "@/api/client";
import { setToken } from "@/utils/auth";
import { setToken, getToken, isTokenExpired } from "@/utils/auth";

export default function Login() {
  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checkingAuth, setCheckingAuth] = useState(true);

  const navigate = useNavigate();

  /**
   * 🔁 Auto redirect
   */
  useEffect(() => {
    const token = getToken();

    if (token && !isTokenExpired(token)) {
      navigate("/dashboard");
    } else {
      setCheckingAuth(false);
    }
  }, [navigate]);

  /**
   * 🔐 Handle Login
   */
  const handleLogin = async () => {
    if (loading) return;

    setError("");

    const email = form.email.trim().toLowerCase();
    const password = form.password.trim();

    if (!email || !password) {
      setError("Please fill all fields");
      return;
    }

    // ✅ Optional email validation
    if (!email.includes("@")) {
      setError("Enter a valid email");
      return;
    }

    try {
      setLoading(true);

      const res = await login({ email, password });

      if (!res?.access_token) {
        throw new Error("Invalid response");
      }

      setToken(res.access_token);

      navigate("/dashboard");

    } catch (err) {
      console.error(err);

      const msg = err.message?.toLowerCase() || "";

      if (msg.includes("invalid")) {
        setError("Invalid email or password");
      } else {
        setError("Something went wrong. Try again.");
      }

    } finally {
      setLoading(false);
    }
  }; // ✅ FIXED (function closed properly)

  /**
   * ⌨️ Enter key support
   */
  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleLogin();
    }
  };

  // ⏳ Avoid flicker
  if (checkingAuth) {
    return <div style={styles.center}>Checking session...</div>;
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>AI Receptionist</h1>

      <p style={styles.subtitle}>
        Manage your appointments, calendar, and usage in one place.
      </p>

      <div style={styles.card}>
        <h2>Login</h2>

        <input
          style={styles.input}
          placeholder="Email"
          value={form.email}
          onChange={(e) =>
            setForm({ ...form, email: e.target.value })
          }
          onKeyDown={handleKeyDown}
        />

        <input
          style={styles.input}
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={(e) =>
            setForm({ ...form, password: e.target.value })
          }
          onKeyDown={handleKeyDown}
        />

        {error && <p style={styles.error}>{error}</p>}

        <button
          onClick={handleLogin}
          style={styles.button}
          disabled={loading}
        >
          {loading ? "Logging in..." : "Login"}
        </button>

        <p style={styles.help}>
          Don’t have an account?{" "}
          <Link to="/signup">Create one</Link>
        </p>
      </div>
    </div>
  );
}

/**
 * 🎨 Styles
 */
const styles = {
  container: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "sans-serif",
    background: "#f5f7fa",
  },
  title: {
    marginBottom: "10px",
  },
  subtitle: {
    marginBottom: "30px",
    color: "#666",
  },
  card: {
    padding: "30px",
    background: "#fff",
    borderRadius: "10px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
    width: "320px",
  },
  input: {
    width: "100%",
    padding: "10px",
    marginTop: "12px",
    borderRadius: "6px",
    border: "1px solid #ccc",
  },
  button: {
    width: "100%",
    marginTop: "20px",
    padding: "10px",
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
  error: {
    color: "red",
    marginTop: "10px",
  },
  help: {
    marginTop: "15px",
    fontSize: "12px",
    color: "#888",
  },
  center: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "100vh",
  },
};