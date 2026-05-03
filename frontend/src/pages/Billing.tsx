import React from 'react';
import { Card } from '@/components/ui/Card';

export const Billing: React.FC = () => (
  <div className="mx-auto max-w-2xl space-y-8">
    <div>
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Billing</h1>
      <p className="text-slate-500 dark:text-slate-400">Billing and invoices are managed outside this dashboard for now.</p>
    </div>
    <Card title="Billing workspace" description="Placeholder until billing endpoints are available.">
      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        Current plans and invoice history are maintained in your onboarding documents.
      </p>
    </Card>
  </div>
);
