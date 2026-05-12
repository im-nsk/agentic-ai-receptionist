import { formatInTimeZone, fromZonedTime } from 'date-fns-tz';

/** Today's calendar date (YYYY-MM-DD) in the given IANA timezone. */
export function todayYmdInTimeZone(timeZone: string): string {
  const tz = timeZone.trim() || 'America/New_York';
  return formatInTimeZone(new Date(), tz, 'yyyy-MM-dd');
}

function parseSlotToMinutesFromMidnight(slot12: string): number | null {
  const m = slot12.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (!m) return null;
  let h = parseInt(m[1], 10);
  const min = parseInt(m[2], 10);
  const ap = m[3].toUpperCase();
  if (Number.isNaN(h) || Number.isNaN(min)) return null;
  if (ap === 'PM' && h !== 12) h += 12;
  if (ap === 'AM' && h === 12) h = 0;
  return h * 60 + min;
}

/** Supports "9:00 AM" and 24h "14:30" as stored in sheets. */
export function parseFlexibleTimeToMinutesFromMidnight(timeStr: string): number | null {
  const s = timeStr.trim();
  const ampm = parseSlotToMinutesFromMidnight(s);
  if (ampm != null) return ampm;
  const m24 = s.match(/^([01]?\d|2[0-3]):([0-5]\d)$/);
  if (!m24) return null;
  const h = parseInt(m24[1], 10);
  const min = parseInt(m24[2], 10);
  if (Number.isNaN(h) || Number.isNaN(min)) return null;
  return h * 60 + min;
}

function instantFromDateAndMinutes(dateIso: string, minutesFromMidnight: number, timeZone: string): Date | null {
  const tz = timeZone.trim() || 'America/New_York';
  const parts = dateIso.trim().split('-').map((x) => parseInt(x, 10));
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) return null;
  const [y, mo, d] = parts;
  const h = Math.floor(minutesFromMidnight / 60);
  const min = minutesFromMidnight % 60;
  const wall = new Date(y, mo - 1, d, h, min, 0, 0);
  return fromZonedTime(wall, tz);
}

/**
 * Interprets dateIso + time as wall time in `timeZone` (matches backend parse + ZoneInfo).
 * Returns true if that instant is at or before now (UTC).
 */
export function isBookingInstantInPast(dateIso: string, timeStr: string, timeZone: string): boolean {
  const mins = parseFlexibleTimeToMinutesFromMidnight(timeStr);
  if (mins == null) return false;
  const instant = instantFromDateAndMinutes(dateIso, mins, timeZone);
  if (!instant) return false;
  return instant.getTime() <= Date.now();
}

/**
 * Interprets dateIso + 12h slot as wall time in `timeZone` (matches backend parse + ZoneInfo).
 * Returns true if that instant is at or before now (UTC).
 */
export function isSlotInPastForTenant(dateIso: string, slot12: string, timeZone: string): boolean {
  return isBookingInstantInPast(dateIso, slot12, timeZone);
}

/** True if `dateIso` (YYYY-MM-DD) is strictly before today's date in the tenant timezone. */
export function isDateBeforeTenantToday(dateIso: string, timeZone: string): boolean {
  const today = todayYmdInTimeZone(timeZone);
  return dateIso.trim() < today;
}
