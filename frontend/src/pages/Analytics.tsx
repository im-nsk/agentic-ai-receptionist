import React, { useCallback, useEffect, useState } from 'react';
import { getBookings } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { Card } from '@/components/ui/Card';
import { BarChart3, Calendar, Percent, Layers } from 'lucide-react';
import {
  aggregateLast7DayCountsFromBookings,
  successRateFromBookings,
  sumConfirmedBookings,
} from '@/utils/bookingStats';

function barHeightClass(count: number, max: number): string {
  if (max <= 0 || count <= 0) return 'h-2';
  const ratio = count / max;
  if (ratio <= 0.25) return 'h-8';
  if (ratio <= 0.5) return 'h-14';
  if (ratio <= 0.75) return 'h-20';
  return 'h-28';
}

export const Analytics: React.FC = () => {
  const toast = useToast();
  const [bookings, setBookings] = useState<Awaited<ReturnType<typeof getBookings>>>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBookings(await getBookings());
    } catch (e) {
      toast.error(getApiErrorMessage(e));
      setBookings([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const total = sumConfirmedBookings(bookings);
  const rate = successRateFromBookings(bookings);
  const week = aggregateLast7DayCountsFromBookings(bookings);
  const peak = Math.max(...week, 0);
  const busiest = peak > 0 ? week.findIndex((x) => x === peak) : -1;
  const dayLabels = Array.from({ length: 7 }, (_, idx) => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    now.setDate(now.getDate() - (6 - idx));
    return now.toLocaleDateString(undefined, { weekday: 'short' });
  });

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400">Track booking performance from your server data</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500 dark:text-slate-400">Loading…</p>}

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
            <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">{busiest >= 0 ? dayLabels[busiest] : '--'}</p>
          </div>
        </Card>
      </div>

      <Card title="Last seven days" description="Confirmed bookings by appointment date">
        <div className="flex h-48 items-end gap-3 border-t border-slate-100 pt-6 dark:border-slate-800">
          {week.map((count, idx) => (
            <div key={`${dayLabels[idx]}-${count}`} className="flex flex-1 flex-col items-center gap-2">
              <div className="flex h-36 w-full items-end justify-center">
                <div
                  className={`w-full max-w-[2rem] rounded-md bg-blue-600 dark:bg-blue-500 ${barHeightClass(
                    count,
                    Math.max(peak, 1)
                  )}`}
                />
              </div>
              <span className="text-[11px] font-semibold uppercase text-slate-500 dark:text-slate-400">{dayLabels[idx]}</span>
            </div>
          ))}
          <div className="hidden w-72 shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-4 lg:block dark:border-slate-800 dark:bg-slate-950">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <BarChart3 className="h-4 w-4" />
              Summary
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Metrics reflect bookings stored for your account. Canonical rows are also written to Google Sheets when configured.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
