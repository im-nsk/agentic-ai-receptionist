import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { resendSignupOtp, verifyOtp } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useAuth } from '@/hooks/AuthContext';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

const PENDING_EMAIL_KEY = 'aireceptionist_pending_verification_email';

export const VerifyEmail: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { loginWithToken } = useAuth();

  const locState = location.state as { email?: string; freshSignup?: boolean } | null;

  const email = useMemo(() => {
    const fromState = typeof locState?.email === 'string' ? locState.email.trim().toLowerCase() : '';
    const fromQs = searchParams.get('email')?.trim().toLowerCase() || '';
    const fromStore = (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(PENDING_EMAIL_KEY)) || '';
    return fromState || fromQs || fromStore.trim().toLowerCase();
  }, [locState?.email, searchParams]);

  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMsg, setResendMsg] = useState('');
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!email) return;
    sessionStorage.setItem(PENDING_EMAIL_KEY, email);
  }, [email]);

  useEffect(() => {
    if (!email) return;
    if (locState?.freshSignup) {
      setCooldownUntil(Date.now() + 30_000);
      navigate(`/verify-email?email=${encodeURIComponent(email)}`, { replace: true, state: { email } });
    }
  }, [email, locState?.freshSignup, navigate]);

  useEffect(() => {
    if (!email) {
      navigate('/signup', { replace: true });
    }
  }, [email, navigate]);

  useEffect(() => {
    if (cooldownUntil <= Date.now()) return;
    const t = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(t);
  }, [cooldownUntil]);

  const coolLeft = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const otp = code.replace(/\s/g, '');
    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
      setError('Enter the 6-digit code.');
      return;
    }
    setIsLoading(true);
    try {
      const res = await verifyOtp({ email, code: otp });
      if (!res.access_token) throw new Error('Invalid response');
      sessionStorage.removeItem(PENDING_EMAIL_KEY);
      loginWithToken(res.access_token);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = useCallback(async () => {
    if (!email || coolLeft > 0 || resendLoading) return;
    setResendMsg('');
    setError('');
    setResendLoading(true);
    try {
      await resendSignupOtp({ email });
      setResendMsg('A new code was sent. Check your inbox.');
      setCooldownUntil(Date.now() + 30_000);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setResendLoading(false);
    }
  }, [email, coolLeft, resendLoading]);

  if (!email) return null;

  return (
    <MinimalPage>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Verify your email</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Enter the code sent to <span className="font-medium text-slate-900 dark:text-slate-100">{email}</span>
          </p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-500">Codes expire in 5 minutes.</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="otp-code">
                6-digit code
              </label>
              <input
                id="otp-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(ev) => setCode(ev.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-center text-2xl font-mono tracking-[0.4em] text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/25 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
              />
            </div>
            {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
            {resendMsg && <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{resendMsg}</p>}
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Verify and continue
            </Button>
          </form>

          <div className="mt-4 flex flex-col gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={resendLoading || coolLeft > 0}
              isLoading={resendLoading}
              onClick={() => void handleResend()}
            >
              {coolLeft > 0 ? `Resend code (${coolLeft}s)` : 'Resend code'}
            </Button>
          </div>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Wrong email?{' '}
            <Link to="/signup" className="font-medium text-blue-600 hover:text-blue-500">
              Sign up again
            </Link>
          </p>
          <p className="mt-3 text-center text-sm text-slate-500 dark:text-slate-400">
            Already verified?{' '}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Sign in
            </Link>
          </p>
        </Card>
      </div>
    </MinimalPage>
  );
};
