import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { forgotPassword } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { MinimalPage } from '@/layout/MinimalPage';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const em = email.trim().toLowerCase();
    if (!em || !em.includes('@')) {
      setError('Enter a valid email.');
      return;
    }
    setIsLoading(true);
    try {
      await forgotPassword({ email: em });
      setDone(true);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MinimalPage>
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Forgot password</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            We&apos;ll email a reset code if this address belongs to a verified account.
          </p>
        </div>

        <Card>
          {done ? (
            <div className="space-y-4 pt-2 text-center text-sm text-slate-600 dark:text-slate-400">
              <p>If an account exists for that email, you&apos;ll receive a code shortly. It expires in 5 minutes.</p>
              <Button
                type="button"
                className="w-full"
                onClick={() =>
                  navigate(`/reset-password?email=${encodeURIComponent(email.trim().toLowerCase())}`)
                }
              >
                Enter reset code
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 pt-2">
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(ev) => setEmail(ev.target.value)}
                placeholder="you@business.com"
                autoComplete="email"
              />
              {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
              <Button type="submit" className="w-full" isLoading={isLoading}>
                Send reset code
              </Button>
            </form>
          )}
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
