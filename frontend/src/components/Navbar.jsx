/**
 * Navbar.jsx (Final Stable Version)
 *
 * - Simple, complete navigation
 * - All pages included
 * - No over-engineering
 */

import { useNavigate, useLocation } from "react-router-dom";
import { logout } from "../utils/auth";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div style={styles.navbar}>
      {/* Logo */}
      <h3 style={styles.logo} onClick={() => navigate("/dashboard")}>
        AI Receptionist
      </h3>

      {/* Links */}
      <div style={styles.links}>
        <button
          onClick={() => navigate("/dashboard")}
          style={{ ...styles.link, ...(isActive("/dashboard") && styles.active) }}
        >
          Dashboard
        </button>

        <button
          onClick={() => navigate("/setup")}
          style={{ ...styles.link, ...(isActive("/setup") && styles.active) }}
        >
          Setup
        </button>

        <button
          onClick={() => navigate("/billing")}
          style={{ ...styles.link, ...(isActive("/billing") && styles.active) }}
        >
          Billing
        </button>

        <button
          onClick={() => navigate("/analytics")}
          style={{ ...styles.link, ...(isActive("/analytics") && styles.active) }}
        >
          Analytics
        </button>

        <button
          onClick={() => navigate("/settings")}
          style={{ ...styles.link, ...(isActive("/settings") && styles.active) }}
        >
          Settings
        </button>

        <button
          onClick={() => {
            logout();
          }}
          style={{ ...styles.link, ...styles.logout }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}

const styles = {
  navbar: {
    height: "60px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 30px",
    background: "#fff",
    borderBottom: "1px solid #eee",
  },
  logo: {
    cursor: "pointer",
  },
  links: {
    display: "flex",
    gap: "10px",
  },
  link: {
    padding: "8px 12px",
    border: "none",
    borderRadius: "6px",
    background: "#f5f5f5",
    cursor: "pointer",
  },
  active: {
    background: "#1677ff",
    color: "#fff",
  },
  logout: {
    background: "#ff4d4f",
    color: "#fff",
  },
};