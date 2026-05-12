import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getSheetAnalytics, type SheetAnalyticsResponse } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ChartSkeleton, StatCardSkeleton } from '@/components/ui/Skeleton';
import { BarChart3, Calendar, Inbox, Layers, Percent, Plug } from 'lucide-react';

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
  const [data, setData] = useState<SheetAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getSheetAnalytics());
    } catch (e) {
      toast.error(getApiErrorMessage(e));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const d = data;
  const ready = !loading && d != null;
  const emptySheet = ready && d.integrations_ready && d.rows_read_ok && d.total_bookings === 0;
  const needsSetup = ready && !d.integrations_ready;
  const readFailed = ready && d.integrations_ready && !d.rows_read_ok;
  const showStats = !needsSetup && !readFailed && (loading || d != null);
  const showChart = !needsSetup && !readFailed && (loading || (d != null && d.rows_read_ok));

  const week = ready && d.rows_read_ok ? d.last_7_days_confirmed_counts : [];
  const peak = week.length ? Math.max(...week, 0) : 0;
  const dayLabels = ready && d.rows_read_ok ? d.last_7_days_labels : [];
  const busiest = ready && d.busiest_day ? `${d.busiest_day.label} (${d.busiest_day.count})` : '—';

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-1 sm:px-0">
      <header className="flex flex-col gap-4 border-b border-slate-200/80 pb-8 dark:border-slate-800/80 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-3xl">Analytics</h1>
          <p className="max-w-xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            All figures are computed on the server from your live Google Sheet — no browser cache and no mock data.
          </p>
        </div>
        <Button type="button" variant="outline" className="shrink-0 self-start sm:self-auto" onClick={() => void load()} disabled={loading} isLoading={loading}>
          Refresh
        </Button>
      </header>

      {needsSetup && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 px-6 py-16 text-center dark:border-slate-600 dark:bg-slate-900/40">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-sm dark:bg-slate-800">
            <Plug className="h-7 w-7 text-slate-500 dark:text-slate-400" />
          </div>
          <div className="max-w-md space-y-2">
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100">Connect your workspace</p>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Add Google Calendar and complete setup so we can read your booking sheet and show real analytics.
            </p>
          </div>
          <Link
            to="/settings"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm shadow-blue-600/25 transition-colors hover:bg-blue-700 active:scale-[0.98] dark:shadow-blue-900/40"
          >
            Open settings
          </Link>
        </div>
      )}

      {readFailed && (
        <div className="rounded-2xl border border-amber-200/90 bg-amber-50/90 px-5 py-4 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/35 dark:text-amber-50">
          We could not read your Google Sheet. Check service account access and try refresh. Metrics stay empty until the sheet is readable.
        </div>
      )}

      {showStats && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {loading || d == null ? (
            <>
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
            </>
          ) : (
            <>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Total bookings</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">{d.total_bookings}</p>
                </div>
              </Card>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                  <Percent className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Success rate</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                    {d.success_rate_percent != null ? `${d.success_rate_percent}%` : '—'}
                  </p>
                </div>
              </Card>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300">
                  <Layers className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Busiest day</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">{busiest}</p>
                </div>
              </Card>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-800 dark:bg-sky-950/50 dark:text-sky-200">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Today ({d.timezone})</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">{d.bookings_today}</p>
                </div>
              </Card>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-200">
                  <Calendar className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">This week</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">{d.bookings_this_week}</p>
                </div>
              </Card>
              <Card className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-800 dark:bg-teal-950/50 dark:text-teal-200">
                  <BarChart3 className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Confirmed / cancelled</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                    {d.confirmed_bookings} / {d.cancelled_bookings}
                  </p>
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {showChart && (
        <Card title="Last seven days" description="Confirmed bookings by appointment date (your business timezone)">
          {loading || d == null ? (
            <ChartSkeleton />
          ) : (
            <div className="flex h-48 flex-col gap-4 border-t border-slate-100 pt-6 dark:border-slate-800 sm:flex-row">
              <div className="flex flex-1 items-end gap-2">
                {week.map((count, idx) => (
                  <div key={`${dayLabels[idx] ?? idx}-${count}`} className="flex flex-1 flex-col items-center gap-2">
                    <div className="flex h-36 w-full items-end justify-center">
                      <div
                        className={`w-full max-w-[2rem] rounded-md bg-blue-600 transition-all dark:bg-blue-500 ${barHeightClass(
                          count,
                          Math.max(peak, 1)
                        )}`}
                      />
                    </div>
                    <span className="text-[11px] font-semibold uppercase text-slate-500 dark:text-slate-400">{dayLabels[idx]}</span>
                  </div>
                ))}
              </div>
              <div className="hidden w-72 shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-4 lg:block dark:border-slate-800 dark:bg-slate-950">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                  <BarChart3 className="h-4 w-4" />
                  Live source
                </div>
                <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  Numbers refresh from Google Sheets on every load. Edits in the sheet appear after you hit Refresh.
                </p>
              </div>
            </div>
          )}
        </Card>
      )}

      {emptySheet && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200/90 bg-white px-6 py-10 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <Inbox className="h-9 w-9 text-slate-400" aria-hidden />
          <p className="text-sm font-medium text-slate-900 dark:text-slate-50">Sheet is connected — waiting for the first booking row</p>
          <p className="max-w-md text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            Figures above are real (zeros until data exists). New bookings from the app, phone assistant, or the sheet will update on the next refresh.
          </p>
        </div>
      )}

      {!loading && d == null && !needsSetup && (
        <p className="text-center text-sm text-slate-600 dark:text-slate-400">Analytics could not be loaded. Try refresh.</p>
      )}
    </div>
  );
};
