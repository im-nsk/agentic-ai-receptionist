/**
 * App.jsx (FINAL Production Safe)
 */

import { Routes, Route, Navigate } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Setup from "./pages/Setup";
import Billing from "./pages/Billing";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";

import AppLayout from "./layout/AppLayout";
import { getToken, isTokenExpired, logout } from "./utils/auth";

/**
 * 🔐 Protected Route
 * - Ensures only authenticated users can access
 * - Clears invalid tokens
 */
function ProtectedRoute({ children }) {
  const token = getToken();

  if (!token || isTokenExpired(token)) {
    logout(); // ✅ important fix
    return <Navigate to="/" replace />;
  }

  return children;
}

/**
 * 🔄 Public Route Guard
 * - Prevent logged-in users from accessing login/signup
 */
function PublicRoute({ children }) {
  const token = getToken();

  if (token && !isTokenExpired(token)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

/**
 * 🔒 Layout Wrapper
 */
function ProtectedLayout({ children }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <Routes>
      {/* 🔓 Public Routes */}
      <Route
        path="/"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      <Route
        path="/signup"
        element={
          <PublicRoute>
            <Signup />
          </PublicRoute>
        }
      />

      {/* 🔒 Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedLayout>
            <Dashboard />
          </ProtectedLayout>
        }
      />

      <Route
        path="/setup"
        element={
          <ProtectedLayout>
            <Setup />
          </ProtectedLayout>
        }
      />

      <Route
        path="/billing"
        element={
          <ProtectedLayout>
            <Billing />
          </ProtectedLayout>
        }
      />

      <Route
        path="/analytics"
        element={
          <ProtectedLayout>
            <Analytics />
          </ProtectedLayout>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedLayout>
            <Settings />
          </ProtectedLayout>
        }
      />

      {/* ❌ Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;