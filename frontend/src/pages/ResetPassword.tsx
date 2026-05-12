import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export const ResetPassword: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const initialEmail = useMemo(() => {
    const s = typeof (location.state as { email?: string } | null)?.email === 'string' ? (location.state as { email: string }).email : '';
    const q = searchParams.get('email')?.trim().toLowerCase() || '';
    return (s.trim().toLowerCase() || q).trim();
  }, [location.state, searchParams]);

  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (initialEmail) setEmail(initialEmail);
  }, [initialEmail]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const em = email.trim().toLowerCase();
    const otp = code.replace(/\s/g, '');
    const pw = newPassword.trim();
    if (!em || !em.includes('@')) {
      toast.error('Enter a valid email.');
      return;
    }
    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
      toast.error('Enter the 6-digit code from your email.');
      return;
    }
    if (pw.length < 6) {
      toast.error('Password must be at least 6 characters.');
      return;
    }
    setIsLoading(true);
    try {
      await resetPassword({ email: em, code: otp, new_password: pw });
      navigate('/login', { replace: true, state: { resetOk: true } });
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MinimalPage>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Reset password</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Enter the code we sent and choose a new password.</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <Input label="Email" type="email" value={email} onChange={(ev) => setEmail(ev.target.value)} autoComplete="email" />
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="reset-code">
                6-digit code
              </label>
              <input
                id="reset-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(ev) => setCode(ev.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-center text-2xl font-mono tracking-[0.4em] text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/25 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
              />
            </div>
            <Input
              label="New password"
              type="password"
              value={newPassword}
              onChange={(ev) => setNewPassword(ev.target.value)}
              placeholder="At least 6 characters"
              autoComplete="new-password"
            />
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Update password
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Back to sign in
            </Link>
          </p>
        </Card>
      </div>
    </MinimalPage>
  );
};
