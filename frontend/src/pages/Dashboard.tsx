import React, { useCallback, useEffect, useState } from 'react';
import { deleteBooking, getBookings, getClient, getSheetAnalytics, patchBooking, type SheetAnalyticsResponse } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { ChartSkeleton, StatCardSkeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Table, TableCell, TableRow } from '@/components/ui/Table';
import { useAuth } from '@/hooks/AuthContext';
import { BarChart3, Calendar, Clock, MoreHorizontal, Phone, Target, XCircle } from 'lucide-react';
import { isBookingInstantInPast } from '@/utils/tenantTime';

function barHeightClass(count: number, max: number): string {
  if (max <= 0 || count <= 0) return 'h-2';
  const ratio = count / max;
  if (ratio <= 0.2) return 'h-8';
  if (ratio <= 0.4) return 'h-14';
  if (ratio <= 0.6) return 'h-20';
  if (ratio <= 0.8) return 'h-28';
  return 'h-32';
}

function statusPillClass(status: string): string {
  const s = status.toLowerCase();
  if (s === 'confirmed' || s === 'booked')
    return 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200';
  if (s === 'cancelled' || s === 'canceled')
    return 'bg-amber-50 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100';
  return 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200';
}

function formatMetric(n: number | null | undefined, ok: boolean): string {
  if (!ok || n == null) return '—';
  return String(n);
}

export const Dashboard: React.FC = () => {
  const { profile } = useAuth();
  const toast = useToast();
  const tenantTz = profile?.timezone?.trim() || 'America/New_York';

  const [bookings, setBookings] = useState<Awaited<ReturnType<typeof getBookings>>>([]);
  const [analytics, setAnalytics] = useState<SheetAnalyticsResponse | null>(null);
  const [analyticsOk, setAnalyticsOk] = useState(true);
  const [setupComplete, setSetupComplete] = useState(true);
  const [loading, setLoading] = useState(true);
  /** True during background reload (keeps metrics visible; avoids full-page skeleton flash). */
  const [refreshing, setRefreshing] = useState(false);
  const [rowBusy, setRowBusy] = useState<number | null>(null);
  const [openMenuRow, setOpenMenuRow] = useState<number | null>(null);
  const [rescheduleRowId, setRescheduleRowId] = useState<number | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('');

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true;
      if (silent) setRefreshing(true);
      else setLoading(true);
      const settled = await Promise.allSettled([getBookings(), getClient(), getSheetAnalytics()]);

      if (settled[0].status === 'fulfilled') {
        setBookings(settled[0].value);
      } else {
        setBookings([]);
        toast.error(getApiErrorMessage(settled[0].reason));
      }

      if (settled[1].status === 'fulfilled') {
        setSetupComplete(Boolean(settled[1].value.setup_complete));
      } else {
        toast.error(getApiErrorMessage(settled[1].reason));
      }

      if (settled[2].status === 'fulfilled') {
        setAnalytics(settled[2].value);
        setAnalyticsOk(true);
      } else {
        setAnalytics(null);
        setAnalyticsOk(false);
        toast.error(getApiErrorMessage(settled[2].reason));
      }

      if (silent) setRefreshing(false);
      else setLoading(false);
    },
    [toast]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const a = analytics;
  const showMetrics = !loading && analyticsOk && a != null;
  const trends = showMetrics ? a.last_7_days_confirmed_counts : [];
  const dayLabels = showMetrics ? a.last_7_days_labels : [];
  const maxTrend = Math.max(...trends, 1);
  const recent = bookings.slice(0, 12);

  const emptyMessage =
    !setupComplete && bookings.length === 0
      ? 'No bookings yet. Connect Google Calendar and your booking sheet in Settings to start recording appointments.'
      : 'No bookings yet — new rows appear here as soon as they are written to your Google Sheet.';

  const beginReschedule = (row: (typeof bookings)[0]) => {
    setOpenMenuRow(null);
    setRescheduleRowId(row.row_id);
    setRescheduleDate(row.date || '');
    setRescheduleTime(row.time || '');
  };

  const submitReschedule = async () => {
    if (rescheduleRowId == null) return;
    const d = rescheduleDate.trim();
    const t = rescheduleTime.trim();
    if (!d || !t) {
      toast.error('Enter both date and time to reschedule.');
      return;
    }
    if (isBookingInstantInPast(d, t, tenantTz)) {
      toast.error('Choose a future date and time in your business timezone.');
      return;
    }
    setRowBusy(rescheduleRowId);
    try {
      await patchBooking(rescheduleRowId, { date: d, time: t });
      setRescheduleRowId(null);
      toast.success('Booking updated in your sheet.');
      await load({ silent: true });
    } catch (e) {
      toast.error(getApiErrorMessage(e));
    } finally {
      setRowBusy(null);
    }
  };

  const handleCancel = async (rowId: number) => {
    if (!window.confirm('Mark this booking as cancelled in the sheet?')) return;
    setRowBusy(rowId);
    setOpenMenuRow(null);
    try {
      await patchBooking(rowId, { status: 'cancelled' });
      toast.success('Booking marked cancelled in your sheet.');
      await load({ silent: true });
    } catch (e) {
      toast.error(getApiErrorMessage(e));
    } finally {
      setRowBusy(null);
    }
  };

  const handleDelete = async (rowId: number) => {
    if (!window.confirm('Permanently delete this row from Google Sheets? This cannot be undone.')) return;
    setRowBusy(rowId);
    setOpenMenuRow(null);
    try {
      await deleteBooking(rowId);
      if (rescheduleRowId === rowId) setRescheduleRowId(null);
      toast.success('Row removed from your sheet.');
      await load({ silent: true });
    } catch (e) {
      toast.error(getApiErrorMessage(e));
    } finally {
      setRowBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-10 px-1 sm:px-0">
      <header className="flex flex-col gap-4 border-b border-slate-200/80 pb-8 dark:border-slate-800/80 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-3xl">
            {profile?.name ? `Hello, ${profile.name}` : 'Dashboard'}
          </h1>
          <p className="max-w-xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            Live metrics from your Google Sheet. Refresh after voice bookings, web bookings, or manual edits in Sheets.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          className="shrink-0 self-start sm:self-auto"
          onClick={() => void load({ silent: true })}
          disabled={loading || refreshing}
          isLoading={refreshing}
        >
          Refresh
        </Button>
      </header>

      {!loading && !analyticsOk && (
        <p className="rounded-2xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
          Analytics could not be loaded. Bookings below may still be current — try refresh or check Google API access.
        </p>
      )}

      <section aria-label="Summary metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          <>
            {Array.from({ length: 8 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </>
        ) : (
          <>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                <Calendar className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Total bookings</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {formatMetric(a?.total_bookings, showMetrics)}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                <Target className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Confirmed</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {formatMetric(a?.confirmed_bookings, showMetrics)}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200">
                <XCircle className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Cancelled</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {formatMetric(a?.cancelled_bookings, showMetrics)}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Success rate</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {showMetrics && a.success_rate_percent != null ? `${a.success_rate_percent}%` : '—'}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-800 dark:bg-sky-950/50 dark:text-sky-200">
                <Clock className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Bookings today</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {formatMetric(a?.bookings_today, showMetrics)}
                </p>
                {showMetrics && <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-500">In {a.timezone}</p>}
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-200">
                <Calendar className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">This week (Mon–Sun)</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {formatMetric(a?.bookings_this_week, showMetrics)}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-800 dark:bg-teal-950/50 dark:text-teal-200">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Busiest day</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">
                  {showMetrics && a.busiest_day ? `${a.busiest_day.label} · ${a.busiest_day.count} confirmed` : '—'}
                </p>
              </div>
            </Card>
            <Card className="flex gap-4 border-slate-200/90 p-5 shadow-sm dark:border-slate-800">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <Clock className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Avg call duration</p>
                <p className="mt-1 text-2xl font-semibold text-slate-500 dark:text-slate-400">—</p>
                <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">Coming soon</p>
              </div>
            </Card>
          </>
        )}
      </section>

      <section aria-label="Booking trends">
        <Card
          className="border-slate-200/90 shadow-sm dark:border-slate-800"
          title="Booking trends"
          description="Confirmed rows by appointment date — last 7 days in your business timezone"
        >
          {loading ? (
            <ChartSkeleton />
          ) : !showMetrics ? (
            <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800">
                <BarChart3 className="h-6 w-6 text-slate-400" />
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Trends unavailable until analytics loads.</p>
            </div>
          ) : (
            <div className="flex h-48 items-end gap-2 border-t border-slate-100 pt-6 dark:border-slate-800">
              {trends.map((count, i) => (
                <div key={`${dayLabels[i] ?? i}-${count}`} className="flex flex-1 flex-col items-center gap-2">
                  <div className="flex h-36 w-full items-end justify-center">
                    <div
                      className={`w-full max-w-[2.5rem] rounded-lg bg-blue-600/90 transition-all dark:bg-blue-500 ${barHeightClass(count, maxTrend)}`}
                    />
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    {dayLabels[i]}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <section aria-label="Recent bookings">
        <Card
          className="border-slate-200/90 shadow-sm dark:border-slate-800"
          title="Recent bookings"
          description="Sheet-backed rows — actions update Google Sheets immediately"
        >
          {recent.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800">
                <Calendar className="h-7 w-7 text-slate-500 dark:text-slate-400" />
              </div>
              <p className="max-w-md text-sm leading-relaxed text-slate-600 dark:text-slate-400">{emptyMessage}</p>
            </div>
          ) : (
            <div className="relative isolate">
              {openMenuRow !== null && (
                <button
                  type="button"
                  className="fixed inset-0 z-[100] cursor-default bg-slate-900/10 dark:bg-black/30"
                  aria-label="Close menu"
                  onClick={() => setOpenMenuRow(null)}
                />
              )}
              <Table className="relative z-[120]" headers={['Guest', 'When', 'Phone', 'Outcome', 'Actions']}>
                {recent.map((row) => (
                  <TableRow key={`${row.row_id}-${row.id}`}>
                    <TableCell className="font-medium text-slate-900 dark:text-slate-100">{row.name}</TableCell>
                    <TableCell>
                      {row.date}{' '}
                      <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                        <Clock className="h-3 w-3" />
                        {row.time}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1 break-all">
                        <Phone className="h-3 w-3 shrink-0 text-slate-400" />
                        {row.phone}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${statusPillClass(row.status)}`}>
                        {row.status}
                      </span>
                    </TableCell>
                    <TableCell className="relative z-[120] w-44 min-w-[8rem]">
                      <button
                        type="button"
                        disabled={rowBusy === row.row_id}
                        onClick={() => setOpenMenuRow((v) => (v === row.row_id ? null : row.row_id))}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                        {rowBusy === row.row_id ? '…' : 'Actions'}
                      </button>
                      {openMenuRow === row.row_id && (
                        <div className="absolute bottom-full right-0 z-[130] mb-1 min-w-[10rem] rounded-xl border border-slate-200 bg-white py-1 shadow-xl dark:border-slate-700 dark:bg-slate-900 sm:bottom-auto sm:top-full sm:mb-0 sm:mt-1">
                          <button
                            type="button"
                            className="block w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                            onClick={() => beginReschedule(row)}
                          >
                            Reschedule
                          </button>
                          <button
                            type="button"
                            className="block w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                            onClick={() => void handleCancel(row.row_id)}
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            className="block w-full px-3 py-2 text-left text-xs font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                            onClick={() => void handleDelete(row.row_id)}
                          >
                            Delete row
                          </button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </Table>
            </div>
          )}
        </Card>
      </section>

      {rescheduleRowId !== null && (
        <Card
          className="border-slate-200/90 shadow-sm dark:border-slate-800"
          title="Reschedule booking"
          description="Updates the Google Sheet row only — the calendar event is not moved automatically."
        >
          <div className="mt-4 grid max-w-lg gap-4 sm:grid-cols-2">
            <Input label="Date (YYYY-MM-DD)" value={rescheduleDate} onChange={(e) => setRescheduleDate(e.target.value)} />
            <Input label="Time" placeholder="14:30 or 2:30 PM" value={rescheduleTime} onChange={(e) => setRescheduleTime(e.target.value)} />
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <Button type="button" isLoading={rowBusy === rescheduleRowId} onClick={() => void submitReschedule()}>
              Save new time
            </Button>
            <Button type="button" variant="outline" disabled={rowBusy === rescheduleRowId} onClick={() => setRescheduleRowId(null)}>
              Close
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};
