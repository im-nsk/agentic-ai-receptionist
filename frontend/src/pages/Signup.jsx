/**
 * Signup.jsx (Production Ready)
 *
 * - Strong validation (email + password)
 * - Prevents duplicate requests
 * - Safe async handling
 * - Clean UX (error + success)
 */
/**
 * Signup.jsx (FINAL Production Safe)
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "@/api/client";

export default function Signup() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const navigate = useNavigate();
  const timerRef = useRef(null);

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  const isValidEmail = (email) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSignup = async () => {
    if (loading) return;

    setError("");
    setSuccess("");

    const name = form.name.trim();
    const email = form.email.trim().toLowerCase();
    const password = form.password.trim();

    if (!name || !email || !password) {
      setError("Please fill all fields");
      return;
    }

    if (!isValidEmail(email)) {
      setError("Enter a valid email address");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    try {
      setLoading(true);

      const res = await signup({ name, email, password });

      // ✅ Validate response
      if (!res || res.status !== "created") {
        throw new Error("Signup failed");
      }

      setSuccess("✅ Account created successfully!");

      timerRef.current = setTimeout(() => {
        navigate("/");
      }, 1500);

    } catch (err) {
      console.error(err);

      const msg = err.message?.toLowerCase() || "";

      if (msg.includes("exists")) {
        setError("Email already registered");
      } else {
        setError("Signup failed. Try again.");
      }

    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>AI Receptionist</h1>

      <p style={styles.subtitle}>
        Create your account to start managing bookings.
      </p>

      <div style={styles.card}>
        <h2>Signup</h2>

        <input
          style={styles.input}
          placeholder="Name"
          value={form.name}
          onChange={(e) =>
            setForm({ ...form, name: e.target.value })
          }
        />

        <input
          style={styles.input}
          placeholder="Email"
          value={form.email}
          onChange={(e) =>
            setForm({ ...form, email: e.target.value })
          }
        />

        <input
          style={styles.input}
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={(e) =>
            setForm({ ...form, password: e.target.value })
          }
        />

        {error && <p style={styles.error}>{error}</p>}
        {success && <p style={styles.success}>{success}</p>}

        <button
          onClick={handleSignup}
          style={styles.button}
          disabled={loading}
        >
          {loading ? "Creating account..." : "Signup"}
        </button>

        <p style={styles.help}>
          Already have an account? <Link to="/">Login</Link>
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
  success: {
    color: "green",
    marginTop: "10px",
  },
  help: {
    marginTop: "15px",
    fontSize: "12px",
    color: "#888",
  },
};