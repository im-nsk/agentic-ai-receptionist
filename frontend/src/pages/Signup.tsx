import React, { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signup as signupApi } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export const Signup: React.FC = () => {
  const navigate = useNavigate();
  const timerRef = useRef<number | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const n = name.trim();
    const em = email.trim().toLowerCase();
    const pw = password.trim();

    if (!n || !em || !pw) {
      setError('Fill in all fields.');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(em)) {
      setError('Enter a valid email.');
      return;
    }
    if (pw.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    try {
      setIsLoading(true);
      const res = await signupApi({ name: n, email: em, password: pw });
      if (res.status !== 'created') throw new Error('Signup failed');
      setSuccess(true);
      timerRef.current = window.setTimeout(() => navigate('/login', { replace: true }), 1000);
    } catch (err) {
      const msg = getApiErrorMessage(err).toLowerCase();
      setError(msg.includes('exists') ? 'That email is already registered.' : getApiErrorMessage(err));
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
            Schedule and confirm appointments instantly
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
            {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
            {success && <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Account created.</p>}
            <Button type="submit" className="w-full" isLoading={isLoading} disabled={success}>
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
