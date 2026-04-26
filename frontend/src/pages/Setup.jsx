/**
 * Setup.jsx (FINAL Production Safe)
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { saveSetup } from "@/api/client";
import { getToken, isTokenExpired, logout } from "@/utils/auth";

export default function Setup() {
  const [calendar, setCalendar] = useState("");
  const [sheet, setSheet] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const navigate = useNavigate();

  const handleSave = async () => {
    if (loading) return;

    setError("");
    setSuccess("");

    // ✅ Basic validation
    if (!calendar || !sheet) {
      setError("Please fill all fields");
      return;
    }

    // ✅ Better validation
    if (!calendar.includes("@")) {
      setError("Enter valid calendar email");
      return;
    }

    if (sheet.length < 20) {
      setError("Invalid Google Sheet ID");
      return;
    }

    try {
      const token = getToken();

      // 🔐 Auth check
      if (!token || isTokenExpired(token)) {
        logout();
        return;
      }

      setLoading(true);

      await saveSetup({
        calendar_id: calendar.trim(),
        sheet_id: sheet.trim(),
      });

      setSuccess("✅ Setup saved successfully!");

      // Redirect after success
      setTimeout(() => navigate("/dashboard"), 1500);

    } catch (err) {
      console.error(err);
      setError("❌ Failed to save setup");

    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2>Setup Your Account</h2>

      <p style={styles.info}>
        Connect your Google Calendar and Google Sheet to start receiving bookings.
      </p>

      {/* Calendar Input */}
      <input
        style={styles.input}
        placeholder="Calendar Email (e.g. your@email.com)"
        value={calendar}
        onChange={(e) => setCalendar(e.target.value)}
      />

      <small style={styles.help}>
        This is where appointments will be created.
      </small>

      {/* Sheet Input */}
      <input
        style={styles.input}
        placeholder="Google Sheet ID"
        value={sheet}
        onChange={(e) => setSheet(e.target.value)}
      />

      <small style={styles.help}>
        Example: docs.google.com/spreadsheets/d/<b>THIS_PART</b>/edit
      </small>

      {/* Error */}
      {error && <p style={styles.error}>{error}</p>}

      {/* Success */}
      {success && <p style={styles.success}>{success}</p>}

      {/* Save Button */}
      <button
        onClick={handleSave}
        style={styles.button}
        disabled={loading}
      >
        {loading ? "Saving..." : "Save Setup"}
      </button>

      {/* Back */}
      <button
        onClick={() => navigate("/dashboard")}
        style={styles.link}
      >
        ← Back to Dashboard
      </button>
    </div>
  );
}

/**
 * 🎨 Styles
 */
const styles = {
  container: {
    padding: "40px",
    maxWidth: "500px",
    margin: "auto",
    fontFamily: "sans-serif",
  },
  input: {
    width: "100%",
    padding: "10px",
    marginTop: "15px",
    borderRadius: "6px",
    border: "1px solid #ccc",
  },
  button: {
    marginTop: "20px",
    padding: "10px",
    width: "100%",
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
  link: {
    marginTop: "15px",
    background: "none",
    border: "none",
    color: "#1677ff",
    cursor: "pointer",
  },
  info: {
    color: "#555",
    marginBottom: "10px",
  },
  help: {
    fontSize: "12px",
    color: "#888",
  },
  error: {
    marginTop: "15px",
    color: "red",
  },
  success: {
    marginTop: "15px",
    color: "green",
  },
};