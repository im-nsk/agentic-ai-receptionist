/**
 * Dashboard.jsx (SaaS Production Ready)
 *
 * - Centralized auth
 * - Retry support
 * - Usage visualization
 * - Better UX states
 */
/**
 * Dashboard.jsx (FINAL Production Safe)
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getClient } from "../api/client";
import { getToken, logout, isTokenExpired } from "../utils/auth";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const token = getToken();

      if (!token || isTokenExpired(token)) {
        logout();
        return;
      }

      const res = await getClient();
      setData(res);

    } catch (err) {
      console.error(err);
      setError("Failed to load dashboard");

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // 🔄 Loading
  if (loading) {
    return <div style={styles.center}>Loading dashboard...</div>;
  }

  // ❌ Error with retry
  if (error) {
    return (
      <div style={styles.centerColumn}>
        <p>{error}</p>
        <button onClick={loadDashboard} style={styles.retry}>
          Retry
        </button>
      </div>
    );
  }

  // ❌ Empty state
  if (!data) {
    return (
      <div style={styles.centerColumn}>
        <p>No data found</p>
        <button onClick={loadDashboard} style={styles.retry}>
          Refresh
        </button>
      </div>
    );
  }

  // ✅ FIX: Safe usage calculation
  const usagePercent =
    data.plan_limit > 0
      ? Math.min((data.minutes_used / data.plan_limit) * 100, 100)
      : 0;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2>Dashboard</h2>

        <div>
          <button
            onClick={() => navigate("/setup")}
            style={styles.button}
          >
            Setup
          </button>

          {/* ✅ FIX: logout only (no double navigation) */}
          <button
            onClick={logout}
            style={{ ...styles.button, background: "#ff4d4f" }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Usage Card */}
      <div style={styles.card}>
        <p><b>Name:</b> {data.name}</p>

        <p>
          <b>Usage:</b> {data.minutes_used} / {data.plan_limit} minutes
        </p>

        {/* Progress bar */}
        <div style={styles.progressContainer}>
          <div
            style={{
              ...styles.progressBar,
              width: `${usagePercent}%`,
              background:
                usagePercent > 80 ? "#ff4d4f" : "#1677ff",
            }}
          />
        </div>

        <p style={styles.percent}>
          {usagePercent.toFixed(1)}% used
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
    padding: "40px",
    fontFamily: "sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px",
  },
  card: {
    padding: "20px",
    border: "1px solid #ddd",
    borderRadius: "10px",
    maxWidth: "450px",
  },
  button: {
    marginLeft: "10px",
    padding: "8px 12px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    background: "#1677ff",
    color: "#fff",
  },
  center: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "100vh",
    fontSize: "18px",
  },
  centerColumn: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    height: "100vh",
    gap: "10px",
  },
  retry: {
    padding: "8px 12px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    background: "#1677ff",
    color: "#fff",
  },
  progressContainer: {
    width: "100%",
    height: "10px",
    background: "#eee",
    borderRadius: "6px",
    marginTop: "10px",
  },
  progressBar: {
    height: "100%",
    borderRadius: "6px",
    transition: "width 0.3s ease",
  },
  percent: {
    marginTop: "8px",
    fontSize: "12px",
    color: "#666",
  },
};