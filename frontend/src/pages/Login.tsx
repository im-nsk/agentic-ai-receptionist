import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login as loginApi } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useAuth } from '@/hooks/AuthContext';
import { MinimalPage } from '@/layout/MinimalPage';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const em = email.trim().toLowerCase();
    const pw = password.trim();
    if (!em || !pw) {
      setError('Enter email and password.');
      return;
    }
    if (!em.includes('@')) {
      setError('Enter a valid email.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await loginApi({ email: em, password: pw });
      if (!response.access_token) throw new Error('Invalid response');
      loginWithToken(response.access_token);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      const raw = getApiErrorMessage(error);
      const lower = raw.toLowerCase();
      if (lower.includes('verify your email')) {
        setError(raw);
      } else if (lower.includes('invalid') || lower.includes('401')) {
        setError('Invalid email or password.');
      } else {
        setError(raw);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MinimalPage>
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-2xl shadow-lg shadow-blue-200/80">
            AR
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Sign in</h1>
          <p className="mt-2 text-slate-500 dark:text-slate-400">Manage bookings and availability in one place</p>
        </div>

        <Card className="p-8">
          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Sign In
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Don't have an account?{' '}
            <Link to="/signup" className="font-medium text-blue-600 hover:text-blue-500">
              Create one
            </Link>
          </p>
        </Card>
      </div>
    </MinimalPage>
  );
};
