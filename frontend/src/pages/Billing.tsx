import React from 'react';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/AuthContext';

export const Billing: React.FC = () => {
  const { profile } = useAuth();
  let usedDisplay: number | null = null;
  let limitDisplay: number | null = null;

  try {
    if (
      profile &&
      typeof profile.minutes_used === 'number' &&
      typeof profile.plan_limit === 'number' &&
      Number.isFinite(profile.minutes_used) &&
      Number.isFinite(profile.plan_limit)
    ) {
      usedDisplay = profile.minutes_used;
      limitDisplay = profile.plan_limit;
    }
  } catch {
    usedDisplay = null;
    limitDisplay = null;
  }

  const pctWidth =
    limitDisplay !== null &&
    limitDisplay > 0 &&
    usedDisplay !== null &&
    Number.isFinite(usedDisplay / limitDisplay)
      ? Math.min(100, (usedDisplay / limitDisplay) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Billing</h1>
        <p className="text-slate-500 dark:text-slate-400">
          Billing UI is intentionally lightweight until invoicing endpoints ship; everything here is safe offline.
        </p>
      </div>

      {usedDisplay !== null && limitDisplay !== null ? (
        <Card title="Plan usage (from workspace)" description="Minutes tracked server-side">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-900 dark:text-slate-50">{usedDisplay}</span> minutes used of{' '}
            <span className="font-semibold text-slate-900 dark:text-slate-50">{limitDisplay}</span> included each cycle.
          </p>
          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-900">
            <div className="h-full rounded-full bg-blue-600 transition-[width] dark:bg-blue-500" style={{ width: `${pctWidth}%` }} />
          </div>
        </Card>
      ) : null}

      <Card title="Invoices & payment method" description="Stripe not connected yet">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          When Stripe (or similar) is wired in, receipts and downloadable invoices surface here automatically. Continue using your
          contract or onboarding paperwork until then — this tab will never crash the app while those APIs are unavailable.
        </p>
      </Card>
    </div>
  );
};
