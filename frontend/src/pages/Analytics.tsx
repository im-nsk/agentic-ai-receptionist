import React from 'react';
import { Card } from '@/components/ui/Card';
import { BarChart3, Calendar, Percent, Layers } from 'lucide-react';
import {
  aggregateLast7DayCounts,
  successRateFromStored,
  sumConfirmedBookings,
} from '@/utils/bookingStorage';

function barHeightClass(count: number, max: number): string {
  if (max <= 0 || count <= 0) return 'h-2';
  const ratio = count / max;
  if (ratio <= 0.25) return 'h-8';
  if (ratio <= 0.5) return 'h-14';
  if (ratio <= 0.75) return 'h-20';
  return 'h-28';
}

export const Analytics: React.FC = () => {
  const total = sumConfirmedBookings();
  const rate = successRateFromStored();
  const week = aggregateLast7DayCounts();
  const peak = Math.max(...week);
  const busiest = peak > 0 ? week.findIndex((x) => x === peak) : -1;
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <div className="space-y-8">
      <div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400">Track booking performance</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="flex gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Total bookings</p>
            <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">{total}</p>
          </div>
        </Card>
        <Card className="flex gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            <Percent className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Success rate</p>
            <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">{rate === null ? '--' : `${rate}%`}</p>
          </div>
        </Card>
        <Card className="flex gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Busiest day</p>
            <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">{busiest >= 0 ? labels[busiest] : '--'}</p>
          </div>
        </Card>
      </div>

      <Card title="Last seven session days" description="Booking trend">
        <div className="flex h-48 items-end gap-3 border-t border-slate-100 pt-6 dark:border-slate-800">
          {week.map((count, idx) => (
            <div key={`${labels[idx]}-${count}`} className="flex flex-1 flex-col items-center gap-2">
              <div className="flex h-36 w-full items-end justify-center">
                <div
                  className={`w-full max-w-[2rem] rounded-md bg-blue-600 dark:bg-blue-500 ${barHeightClass(
                    count,
                    Math.max(peak, 1)
                  )}`}
                />
              </div>
              <span className="text-[11px] font-semibold uppercase text-slate-500 dark:text-slate-400">{labels[idx]}</span>
            </div>
          ))}
          <div className="hidden w-72 shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-4 lg:block dark:border-slate-800 dark:bg-slate-950">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <BarChart3 className="h-4 w-4" />
              Summary
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Session-level trend only. Canonical records remain in Google Sheets.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
