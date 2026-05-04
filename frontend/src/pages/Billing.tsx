import React from 'react';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/AuthContext';

export const Billing: React.FC = () => {
  const { profile } = useAuth();
  const used = profile?.minutes_used ?? null;
  const limit = profile?.plan_limit ?? null;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Billing</h1>
        <p className="text-slate-500 dark:text-slate-400">
          Billing and invoicing will connect here soon. Until then everything below is informational.
        </p>
      </div>

      {used !== null && limit !== null ? (
        <Card title="Plan usage (from workspace)" description="Minutes tracked server-side">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-900 dark:text-slate-50">{used}</span> minutes used of{' '}
            <span className="font-semibold text-slate-900 dark:text-slate-50">{limit}</span> included each cycle.
          </p>
          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
            <div
              className="h-full rounded-full bg-blue-600 transition-[width] dark:bg-blue-500"
              style={{ width: `${Math.min(100, limit > 0 ? (used / limit) * 100 : 0)}%` }}
            />
          </div>
        </Card>
      ) : null}

      <Card title="Invoices & payment method" description="No payment processor connected yet">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          When Stripe or another billing provider is wired up, receipts and invoices will appear in this workspace. For now,
          contractual billing follows your onboarding paperwork.
        </p>
      </Card>
    </div>
  );
};
