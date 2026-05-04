import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { verifyOtp } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useAuth } from '@/hooks/AuthContext';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

export const VerifyEmail: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const email =
    typeof (location.state as { email?: string } | null)?.email === 'string'
      ? (location.state as { email: string }).email.trim().toLowerCase()
      : '';
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { loginWithToken } = useAuth();

  useEffect(() => {
    if (!email) {
      navigate('/signup', { replace: true });
    }
  }, [email, navigate]);

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
      loginWithToken(res.access_token);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  if (!email) return null;

  return (
    <MinimalPage>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Verify your email</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Enter the OTP sent to <span className="font-medium text-slate-900 dark:text-slate-100">{email}</span>
          </p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-500">
            MVP: check the backend console for your code if mail is not configured.
          </p>
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
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Verify and continue
            </Button>
          </form>
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
