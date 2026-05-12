import React, { useEffect, useMemo, useState } from 'react';
import { BookResponse, bookAppointment, checkAvailability } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { MonthCalendar } from '@/components/MonthCalendar';
import { useToast } from '@/components/toast/ToastContext';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/AuthContext';
import { getClientIdFromToken } from '@/utils/auth';
import { toISODateLocal } from '@/utils/date';
import { phoneFieldError, normalizeAndValidatePhone } from '@/utils/phone';
import { buildBookingDaySlots } from '@/utils/slots';
import { isSlotInPastForTenant, todayYmdInTimeZone } from '@/utils/tenantTime';

export const Booking: React.FC = () => {
  const { profile } = useAuth();
  const toast = useToast();
  const tenantTz = profile?.timezone?.trim() || 'America/New_York';

  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  });
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [message, setMessage] = useState<string>('');

  const minSelectableYmd = useMemo(() => todayYmdInTimeZone(tenantTz), [tenantTz]);

  const timeSlots = useMemo(
    () => buildBookingDaySlots(profile?.slot_duration ?? 30, profile?.working_hours ?? null),
    [profile?.slot_duration, profile?.working_hours]
  );

  const slotsLayoutKey = useMemo(() => timeSlots.join('|'), [timeSlots]);

  useEffect(() => {
    setSelectedTime(null);
    setAvailable(null);
    setMessage('');
  }, [slotsLayoutKey]);

  useEffect(() => {
    const cur = toISODateLocal(selectedDate);
    if (cur < minSelectableYmd) {
      const [y, m, d] = minSelectableYmd.split('-').map(Number);
      setSelectedDate(new Date(y, m - 1, d));
    }
  }, [minSelectableYmd, selectedDate]);

  const dateIso = toISODateLocal(selectedDate);

  const checkSlot = async (time: string) => {
    const clientId = getClientIdFromToken();
    if (!clientId) return;
    if (isSlotInPastForTenant(dateIso, time, tenantTz)) {
      setAvailable(false);
      setMessage('That time has already passed for your business timezone.');
      return;
    }
    setChecking(true);
    setAvailable(null);
    setMessage('');
    try {
      const res = await checkAvailability({
        client_id: clientId,
        name: 'check',
        phone: '0000000000',
        date: dateIso,
        time,
      });
      setAvailable(res.available);
      setMessage(res.message);
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setChecking(false);
    }
  };

  const handleBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    const clientId = getClientIdFromToken();
    const cleanName = name.trim();
    const cleanPhone = phone.trim();
    if (!clientId) {
      toast.error('Session expired. Sign in again.');
      return;
    }
    if (!selectedTime || !cleanName || !cleanPhone) {
      toast.error('Fill all booking fields.');
      return;
    }
    const phoneErr = phoneFieldError(cleanPhone);
    if (phoneErr) {
      toast.error(phoneErr);
      return;
    }
    if (isSlotInPastForTenant(dateIso, selectedTime, tenantTz)) {
      toast.error('That time has already passed for your business timezone.');
      return;
    }
    if (available !== true) {
      toast.error('Choose an available time slot.');
      return;
    }
    setIsLoading(true);
    try {
      const normalizedPhone = normalizeAndValidatePhone(cleanPhone);
      const res: BookResponse = await bookAppointment({
        client_id: clientId,
        name: cleanName,
        phone: normalizedPhone,
        date: dateIso,
        time: selectedTime,
      });
      const ok = res.status === 'confirmed';
      if (!ok) {
        toast.error(res.message || 'Slot could not be confirmed.');
      } else {
        setName('');
        setPhone('');
        setSelectedTime(null);
        setAvailable(null);
        setMessage('');
        toast.success(res.message || 'Booking confirmed. SMS may follow if SMS is configured.');
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Booking</h1>
          <p className="text-slate-500 dark:text-slate-400">Schedule and confirm appointments instantly</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-5 xl:col-span-4" title="Calendar" description="Select booking day">
          <MonthCalendar selected={selectedDate} onSelect={setSelectedDate} minSelectableDateIso={minSelectableYmd} />
          <p className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-400">
            Selected:&nbsp;
            <strong className="text-slate-900 dark:text-slate-100">
              {selectedDate.toLocaleDateString(undefined, {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric',
              })}
            </strong>
          </p>
        </Card>

        <div className="space-y-6 lg:col-span-7 xl:col-span-8">
          <Card
            title="Time slots"
            description={`${profile?.slot_duration ?? 30}-minute grid from your daily window in Settings (timezone: ${tenantTz}).`}
          >
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
              {timeSlots.length === 0 ? (
                <p className="col-span-full text-sm text-slate-600 dark:text-slate-400">
                  No slots for this configuration — widen your daily booking window or shorten slot duration in Settings.
                </p>
              ) : (
                timeSlots.map((slot) => {
                const past = isSlotInPastForTenant(dateIso, slot, tenantTz);
                return (
                  <button
                    key={slot}
                    type="button"
                    disabled={past}
                    onClick={() => {
                      if (past) return;
                      setSelectedTime(slot);
                      void checkSlot(slot);
                    }}
                    className={`rounded-xl border px-2 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wide transition-colors sm:text-xs ${
                      past
                        ? 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-600'
                        : selectedTime === slot
                          ? 'border-blue-600 bg-blue-600 text-white shadow-md shadow-blue-600/25'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-blue-400 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900'
                    }`}
                  >
                    {slot}
                  </button>
                );
              })
              )}
            </div>
            {checking && <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">Checking slot...</p>}
            {selectedTime && !checking && message && (
              <p
                className={`mt-3 text-sm ${
                  available === true
                    ? 'text-emerald-700 dark:text-emerald-300'
                    : available === false
                      ? 'text-amber-800 dark:text-amber-200'
                      : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                {message}
              </p>
            )}
          </Card>

          <Card title="Booking form">
            <form className="space-y-4" onSubmit={handleBooking}>
              <Input label="Guest name" placeholder="John Doe" value={name} onChange={(e) => setName(e.target.value)} disabled={isLoading} />
              <Input label="Phone number" placeholder="+1 234 567 8900" value={phone} onChange={(e) => setPhone(e.target.value)} disabled={isLoading} />
              <Button type="submit" className="w-full sm:w-auto" isLoading={isLoading} disabled={available !== true}>
                Confirm booking
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
};
