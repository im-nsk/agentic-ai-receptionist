import React, { useCallback, useEffect, useState } from 'react';
import { getBookings, getClient } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { Card } from '@/components/ui/Card';
import { Table, TableCell, TableRow } from '@/components/ui/Table';
import { BarChart3, Calendar, Clock, Phone, Target } from 'lucide-react';
import { useAuth } from '@/hooks/AuthContext';
import {
  aggregateLast7DayCountsFromBookings,
  successRateFromBookings,
  sumConfirmedBookings,
} from '@/utils/bookingStats';

function barHeightClass(count: number, max: number): string {
  if (max <= 0 || count <= 0) return 'h-2';
  const ratio = count / max;
  if (ratio <= 0.2) return 'h-8';
  if (ratio <= 0.4) return 'h-14';
  if (ratio <= 0.6) return 'h-20';
  if (ratio <= 0.8) return 'h-28';
  return 'h-32';
}

export const Dashboard: React.FC = () => {
  const { profile } = useAuth();
  const [bookings, setBookings] = useState<Awaited<ReturnType<typeof getBookings>>>([]);
  const [setupComplete, setSetupComplete] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [rows, client] = await Promise.all([getBookings(), getClient()]);
      setBookings(rows);
      setSetupComplete(Boolean(client.setup_complete));
    } catch (e) {
      setLoadError(getApiErrorMessage(e));
      setBookings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const totalBookings = sumConfirmedBookings(bookings);
  const successRate = successRateFromBookings(bookings);
  const trends = aggregateLast7DayCountsFromBookings(bookings);
  const maxTrend = Math.max(...trends, 1);
  const recent = bookings.slice(0, 8);

  const dayLabels = Array.from({ length: 7 }, (_, idx) => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    now.setDate(now.getDate() - (6 - idx));
    return now.toLocaleDateString(undefined, { weekday: 'short' });
  });

  const emptyMessage =
    !setupComplete && bookings.length === 0
      ? 'No bookings yet. Connect Google Calendar and Sheet in Settings to record bookings.'
      : 'No bookings yet';

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            {profile?.name ? `Hello, ${profile.name}` : 'Dashboard'}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Track booking performance</p>
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

      {loadError && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-50">
          {loadError}{' '}
          <button type="button" onClick={() => void load()} className="underline">
            Retry
          </button>
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="flex gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Total bookings
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">{totalBookings}</p>
          </div>
        </Card>
        <Card className="flex gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            <Target className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Success rate
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
              {successRate === null ? '--' : `${successRate}%`}
            </p>
          </div>
        </Card>
        <Card className="flex gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Avg call duration
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">--</p>
          </div>
        </Card>
        <Card className="flex gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              This week
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
              {trends.reduce((a, b) => a + b, 0)}
            </p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card title="Booking trends" description="Last seven days (confirmed bookings by date)">
          <div className="flex h-48 items-end gap-2 border-t border-slate-100 pt-6 dark:border-slate-800">
            {trends.map((count, i) => (
              <div key={`${dayLabels[i]}-${count}`} className="flex flex-1 flex-col items-center gap-2">
                <div className="flex h-36 w-full items-end justify-center">
                  <div
                    className={`w-full max-w-[2.5rem] rounded-lg bg-blue-600/90 dark:bg-blue-500 ${barHeightClass(count, maxTrend)}`}
                  />
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {dayLabels[i]}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Recent bookings" description="Latest activity from your workspace">
        {recent.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</p>
        ) : (
          <Table headers={['Guest', 'When', 'Phone', 'Outcome']}>
            {recent.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-medium text-slate-900 dark:text-slate-100">{row.name}</TableCell>
                <TableCell>
                  {row.date}{' '}
                  <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                    <Clock className="h-3 w-3" />
                    {row.time}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1">
                    <Phone className="h-3 w-3 text-slate-400" />
                    {row.phone}
                  </span>
                </TableCell>
                <TableCell>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                      row.status === 'confirmed'
                        ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200'
                        : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200'
                    }`}
                  >
                    {row.status}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
};
