import React, { useCallback, useEffect, useState } from 'react';
import { deleteBooking, getBookings, getClient, patchBooking } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Table, TableCell, TableRow } from '@/components/ui/Table';
import { useAuth } from '@/hooks/AuthContext';
import { BarChart3, Calendar, Clock, MoreHorizontal, Phone, Target } from 'lucide-react';
import {
  aggregateLast7DayCountsFromBookings,
  successRateFromBookings,
  sumConfirmedBookings,
} from '@/utils/bookingStats';
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

export const Dashboard: React.FC = () => {
  const { profile } = useAuth();
  const toast = useToast();
  const tenantTz = profile?.timezone?.trim() || 'America/New_York';

  const [bookings, setBookings] = useState<Awaited<ReturnType<typeof getBookings>>>([]);
  const [setupComplete, setSetupComplete] = useState(true);
  const [loading, setLoading] = useState(true);
  const [rowBusy, setRowBusy] = useState<number | null>(null);
  const [openMenuRow, setOpenMenuRow] = useState<number | null>(null);
  const [rescheduleRowId, setRescheduleRowId] = useState<number | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, client] = await Promise.all([getBookings(), getClient()]);
      setBookings(rows);
      setSetupComplete(Boolean(client.setup_complete));
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

  const totalBookings = sumConfirmedBookings(bookings);
  const successRate = successRateFromBookings(bookings);
  const trends = aggregateLast7DayCountsFromBookings(bookings);
  const maxTrend = Math.max(...trends, 1);
  const recent = bookings.slice(0, 12);

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
      await load();
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
      await load();
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
      await load();
    } catch (e) {
      toast.error(getApiErrorMessage(e));
    } finally {
      setRowBusy(null);
    }
  };

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

      <Card title="Recent bookings" description="Live data from your Google Sheet (row actions update the sheet)">
        {recent.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</p>
        ) : (
          <>
            <Table headers={['Guest', 'When', 'Phone', 'Outcome', 'Actions']}>
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
                    <span className="inline-flex items-center gap-1">
                      <Phone className="h-3 w-3 text-slate-400" />
                      {row.phone}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${statusPillClass(row.status)}`}>
                      {row.status}
                    </span>
                  </TableCell>
                  <TableCell className="relative w-44">
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
                      <div className="absolute right-0 top-full z-[110] mt-1 min-w-[10rem] rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
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
            {openMenuRow !== null && (
              <button
                type="button"
                className="fixed inset-0 z-[100] cursor-default bg-slate-900/10 dark:bg-black/30"
                aria-label="Close menu"
                onClick={() => setOpenMenuRow(null)}
              />
            )}
          </>
        )}
      </Card>

      {rescheduleRowId !== null && (
        <Card title="Reschedule booking" description="Updates the Google Sheet row (calendar event is not moved automatically).">
          <div className="mt-4 grid max-w-md gap-4 sm:grid-cols-2">
            <Input label="Date (YYYY-MM-DD)" value={rescheduleDate} onChange={(e) => setRescheduleDate(e.target.value)} />
            <Input label="Time" placeholder="14:30 or 2:30 PM" value={rescheduleTime} onChange={(e) => setRescheduleTime(e.target.value)} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
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
