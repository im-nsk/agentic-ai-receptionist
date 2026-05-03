import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import {
  Calendar as CalendarIcon,
  Download,
  Search,
  Clock,
} from 'lucide-react';
import client from '../api/client';
import { cn } from '../lib/utils';

function generateSlots(start: string, end: string, interval: number) {
  const slots: string[] = [];

  let current = new Date(`1970-01-01T${start}:00`);
  const endTime = new Date(`1970-01-01T${end}:00`);

  while (current < endTime) {
    const formatted = new Date(current).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    slots.push(formatted);
    current.setMinutes(current.getMinutes() + interval);
  }

  return slots;
}

export const Booking: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'schedule' | 'records'>('schedule');
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Config (later move to settings/backend)
  const timeSlots = useMemo(
    () => generateSlots('09:00', '17:00', 30),
    []
  );

  useEffect(() => {
    setMessage(null);
  }, [selectedDate, selectedTime]);

  const handleBooking = async (e: React.FormEvent) => {
    e.preventDefault();

    if (customerName.trim().length < 2) {
      setMessage({ type: 'error', text: 'Enter valid name' });
      return;
    }

    if (phoneNumber.replace(/\D/g, '').length < 8) {
      setMessage({ type: 'error', text: 'Enter valid phone number' });
      return;
    }

    if (!selectedDate || !selectedTime) {
      setMessage({ type: 'error', text: 'Select date and time' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    const payload = {
      date: selectedDate,
      time: selectedTime,
      name: customerName.trim(),
      phone: phoneNumber,
    };

    try {
      setChecking(true);
      const availRes = await client.post('/check-availability', payload);
      setChecking(false);

      if (!availRes.data.available) {
        setMessage({
          type: 'error',
          text: availRes.data.message || 'Slot not available',
        });
        return;
      }

      await client.post('/book-appointment', payload);

      setMessage({
        type: 'success',
        text: 'Appointment booked successfully!',
      });

      setCustomerName('');
      setPhoneNumber('');
      setSelectedTime(null);

    } catch (error: any) {
      const errorMsg =
        error?.message ||
        error?.response?.data?.detail ||
        'Failed to book appointment';

      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setIsLoading(false);
      setChecking(false);
    }
  };

  const today = new Date();

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Booking Management</h1>
          <p className="text-slate-500">Organize and manage appointments.</p>
        </div>

        <div className="inline-flex rounded-xl bg-white p-1 border">
          <button
            onClick={() => setActiveTab('schedule')}
            className={`px-4 py-1.5 text-xs font-bold ${
              activeTab === 'schedule' ? 'bg-blue-600 text-white' : 'text-slate-500'
            }`}
          >
            Schedule
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`px-4 py-1.5 text-xs font-bold ${
              activeTab === 'records' ? 'bg-blue-600 text-white' : 'text-slate-500'
            }`}
          >
            Records
          </button>
        </div>
      </div>

      {activeTab === 'schedule' ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <Card className="lg:col-span-7" title="Select Date">
            <div className="grid grid-cols-7 gap-2">
              {Array.from({ length: 31 }).map((_, i) => {
                const dateObj = new Date(
                  today.getFullYear(),
                  today.getMonth(),
                  i + 1
                );
                const iso = dateObj.toISOString().split('T')[0];

                return (
                  <button
                    key={i}
                    onClick={() => setSelectedDate(iso)}
                    className={`h-10 rounded-xl border ${
                      selectedDate === iso
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-slate-600'
                    }`}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>

            <div className="mt-4 text-sm text-slate-600">
              Selected: {selectedDate}
            </div>
          </Card>

          <div className="lg:col-span-5 space-y-6">
            <Card title="Time Slots">
              <div className="grid grid-cols-3 gap-2">
                {timeSlots.map((slot) => (
                  <button
                    key={slot}
                    onClick={() => setSelectedTime(slot)}
                    className={`rounded-xl py-2 text-xs font-bold border ${
                      selectedTime === slot
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-slate-600'
                    }`}
                  >
                    {slot}
                  </button>
                ))}
              </div>

              {checking && (
                <p className="mt-3 text-sm text-slate-500">
                  Checking availability...
                </p>
              )}
            </Card>

            <Card title="Booking Details">
              <form onSubmit={handleBooking} className="space-y-4">
                <Input
                  label="Customer Name"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                />

                <Input
                  label="Phone Number"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />

                {message && (
                  <p
                    className={cn(
                      'text-sm text-center',
                      message.type === 'success'
                        ? 'text-green-600'
                        : 'text-red-500'
                    )}
                  >
                    {message.text}
                  </p>
                )}

                <Button
                  type="submit"
                  isLoading={isLoading}
                  disabled={!selectedTime}
                >
                  Confirm Booking
                </Button>
              </form>
            </Card>
          </div>
        </div>
      ) : (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 rounded-full bg-slate-100 p-4">
              <CalendarIcon className="h-6 w-6 text-slate-500" />
            </div>

            <h3 className="text-lg font-semibold text-slate-900">
              No bookings yet
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              Create your first booking from the schedule tab.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};