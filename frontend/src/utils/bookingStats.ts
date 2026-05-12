import type { BookingRowResponse } from '@/api/client';
import { toISODateLocal } from '@/utils/date';

export function aggregateLast7DayCountsFromBookings(bookings: BookingRowResponse[]): number[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const counts = [0, 0, 0, 0, 0, 0, 0];

  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = new Date(today);
    day.setDate(today.getDate() - offset);
    const iso = toISODateLocal(day);
    counts[6 - offset] = bookings.filter((b) => b.date === iso && b.status === 'confirmed').length;
  }

  return counts;
}

export function sumConfirmedBookings(bookings: BookingRowResponse[]): number {
  return bookings.filter((b) => b.status === 'confirmed').length;
}

export function successRateFromBookings(bookings: BookingRowResponse[]): number | null {
  if (bookings.length === 0) return null;
  const confirmed = bookings.filter((b) => b.status === 'confirmed').length;
  return Math.round((confirmed / bookings.length) * 1000) / 10;
}
