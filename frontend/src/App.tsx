import React, { useEffect, useRef } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { useToast } from '@/components/toast/ToastContext';
import { AuthProvider, useAuth } from '@/hooks/AuthContext';
import { MainLayout } from '@/layout/MainLayout';
import { getToken, isTokenExpired } from '@/utils/auth';
import { Analytics } from '@/pages/Analytics';
import { Billing } from '@/pages/Billing';
import { Booking } from '@/pages/Booking';
import { Dashboard } from '@/pages/Dashboard';
import { ForgotPassword } from '@/pages/ForgotPassword';
import { Login } from '@/pages/Login';
import { ResetPassword } from '@/pages/ResetPassword';
import { Settings } from '@/pages/Settings';
import { Signup } from '@/pages/Signup';
import { VerifyEmail } from '@/pages/VerifyEmail';

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
  const toast = useToast();
  const token = getToken();
  const lastProfileErr = useRef<string | null>(null);

  useEffect(() => {
    if (profileError && profileError !== lastProfileErr.current) {
      lastProfileErr.current = profileError;
      toast.error(profileError);
    }
    if (!profileError) lastProfileErr.current = null;
  }, [profileError, toast]);

  if (!token || isTokenExpired(token)) {
    return <Navigate to="/login" replace />;
  }

  if (profileLoading) {
    return <Spinner />;
  }

  return (
    <>
      <Outlet />
      {profileError && (
        <div className="fixed bottom-4 left-4 z-[150]">
          <button
            type="button"
            onClick={() => void refreshProfile()}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-800 shadow-md hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            Retry profile
          </button>
        </div>
      )}
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
        <Route
          path="/verify-email"
          element={
            <GuestShell>
              <VerifyEmail />
            </GuestShell>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <GuestShell>
              <ForgotPassword />
            </GuestShell>
          }
        />
        <Route
          path="/reset-password"
          element={
            <GuestShell>
              <ResetPassword />
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
