import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup as signupApi } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export const Signup: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const n = name.trim();
    const em = email.trim().toLowerCase();
    const pw = password.trim();

    if (!n || !em || !pw) {
      toast.error('Fill in all fields.');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(em)) {
      toast.error('Enter a valid email.');
      return;
    }
    if (pw.length < 6) {
      toast.error('Password must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    try {
      await signupApi({ name: n, email: em, password: pw });
      try {
        sessionStorage.setItem('aireceptionist_pending_verification_email', em);
      } catch {
        /* ignore */
      }
      navigate(`/verify-email?email=${encodeURIComponent(em)}`, {
        replace: true,
        state: { email: em, freshSignup: true },
      });
    } catch (err) {
      const raw = getApiErrorMessage(err);
      const msg = raw.toLowerCase();
      toast.error(
        msg.includes('exists') || msg.includes('already') || msg.includes('registered')
          ? 'That email is already registered.'
          : raw
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MinimalPage>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 font-semibold text-white shadow-lg shadow-blue-600/25">
            AR
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Create account</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            We&apos;ll email you a one-time code to verify your address (if email is not configured, the server logs the code in development).
          </p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <Input label="Name" value={name} onChange={(ev) => setName(ev.target.value)} placeholder="Business name" />
            <Input label="Email" type="email" value={email} onChange={(ev) => setEmail(ev.target.value)} placeholder="you@business.com" />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              placeholder="At least 6 characters"
            />
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Create account
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Already registered?{' '}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Sign in
            </Link>
          </p>
        </Card>
      </div>
    </MinimalPage>
  );
};
