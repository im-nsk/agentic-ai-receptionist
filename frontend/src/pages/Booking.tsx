import React, { useState } from 'react';
import { BookResponse, bookAppointment, checkAvailability } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { MonthCalendar } from '@/components/MonthCalendar';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { getClientIdFromToken } from '@/utils/auth';
import { addStoredBooking, toISODateLocal } from '@/utils/bookingStorage';
import { WORK_TIME_SLOTS } from '@/utils/slots';

export const Booking: React.FC = () => {
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
  const [error, setError] = useState('');

  const dateIso = toISODateLocal(selectedDate);

  const checkSlot = async (time: string) => {
    const clientId = getClientIdFromToken();
    if (!clientId) return;
    setChecking(true);
    setAvailable(null);
    setError('');
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
      setError(getApiErrorMessage(err));
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
      setError('Session expired. Sign in again.');
      return;
    }
    if (!selectedTime || !cleanName || !cleanPhone) {
      setError('Fill all booking fields.');
      return;
    }
    if (available !== true) {
      setError('Choose an available time slot.');
      return;
    }
    setIsLoading(true);
    setError('');
    setMessage('');
    try {
      const res: BookResponse = await bookAppointment({
        client_id: clientId,
        name: cleanName,
        phone: cleanPhone,
        date: dateIso,
        time: selectedTime,
      });
      const ok = res.status === 'confirmed';
      addStoredBooking({
        name: cleanName,
        phone: cleanPhone,
        date: dateIso,
        time: selectedTime,
        status: ok ? 'confirmed' : 'failed',
      });
      if (!ok) {
        setError('Slot could not be confirmed.');
      } else {
        setName('');
        setPhone('');
        setSelectedTime(null);
        setAvailable(null);
        setMessage('Appointment confirmed.');
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
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
          <MonthCalendar selected={selectedDate} onSelect={setSelectedDate} />
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
          <Card title="Time slots" description="Check availability before booking">
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
              {WORK_TIME_SLOTS.map((slot) => (
                <button
                  key={slot}
                  type="button"
                  onClick={() => {
                    setSelectedTime(slot);
                    void checkSlot(slot);
                  }}
                  className={`rounded-xl border px-2 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wide transition-colors sm:text-xs ${
                    selectedTime === slot
                      ? 'border-blue-600 bg-blue-600 text-white shadow-md shadow-blue-600/25'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-blue-400 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900'
                  }`}
                >
                  {slot}
                </button>
              ))}
            </div>
            {checking && <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">Checking slot...</p>}
            {selectedTime && !checking && message && available === true && (
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-100">
                {message}
              </div>
            )}
            {selectedTime && !checking && message && available === false && (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-50">
                {message}
              </div>
            )}
          </Card>

          <Card title="Booking form">
            <form className="space-y-4" onSubmit={handleBooking}>
              <Input label="Guest name" placeholder="John Doe" value={name} onChange={(e) => setName(e.target.value)} disabled={isLoading} />
              <Input label="Phone number" placeholder="+1 234 567 8900" value={phone} onChange={(e) => setPhone(e.target.value)} disabled={isLoading} />
              {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
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
