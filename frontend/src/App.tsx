import React from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/hooks/AuthContext';
import { MainLayout } from '@/layout/MainLayout';
import { getToken, isTokenExpired } from '@/utils/auth';
import { Analytics } from '@/pages/Analytics';
import { Billing } from '@/pages/Billing';
import { Booking } from '@/pages/Booking';
import { Dashboard } from '@/pages/Dashboard';
import { Login } from '@/pages/Login';
import { Settings } from '@/pages/Settings';
import { Signup } from '@/pages/Signup';

function Spinner() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 dark:bg-slate-950">
      <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-blue-600 border-t-transparent" />
      <p className="text-sm text-slate-500 dark:text-slate-400">Loading workspace...</p>
    </div>
  );
}

function ProtectedShell() {
  const { profileLoading, profileError, refreshProfile } = useAuth();
  const token = getToken();

  if (!token || isTokenExpired(token)) {
    return <Navigate to="/login" replace />;
  }

  if (profileLoading) {
    return <Spinner />;
  }

  return (
    <>
      {profileError && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 sm:px-6 lg:px-8">
            <span>{profileError}</span>
            <button
              type="button"
              onClick={() => void refreshProfile()}
              className="rounded-lg bg-amber-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-amber-900 hover:bg-amber-200 dark:bg-amber-900/60 dark:text-amber-50 dark:hover:bg-amber-800/80"
            >
              Retry
            </button>
          </div>
        </div>
      )}
      <Outlet />
    </>
  );
}

function GuestShell({ children }: { children: React.ReactNode }) {
  const token = getToken();
  if (token && !isTokenExpired(token)) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function RootRedirect() {
  const token = getToken();
  if (!token || isTokenExpired(token)) {
    return <Navigate to="/login" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestShell>
              <Login />
            </GuestShell>
          }
        />
        <Route
          path="/signup"
          element={
            <GuestShell>
              <Signup />
            </GuestShell>
          }
        />

        <Route element={<ProtectedShell />}>
          <Route element={<MainLayout />}>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/booking" element={<Booking />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}