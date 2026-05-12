import { dailyWindowMinutesFromWorkingHours } from '@/utils/slots';

export const WEEKDAY_KEYS = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
] as const;

export type WeekdayKey = (typeof WEEKDAY_KEYS)[number];

export type DaySchedule = { enabled: boolean; start: string; end: string };

export type WeeklyAvailability = Record<WeekdayKey, DaySchedule>;

const HH_MM = /^([01]?\d|2[0-3]):([0-5]\d)$/;

function parseHourMinuteToMinutes(s: string): number | null {
  const m = s.trim().match(HH_MM);
  if (!m) return null;
  const h = parseInt(m[1], 10);
  const min = parseInt(m[2], 10);
  if (Number.isNaN(h) || Number.isNaN(min) || h < 0 || h > 23 || min < 0 || min > 59) return null;
  return h * 60 + min;
}

function format12FromMinutes(totalMinutes: number): string {
  const normalized = ((totalMinutes % (24 * 60)) + 24 * 60) % (24 * 60);
  const h24 = Math.floor(normalized / 60);
  const minute = normalized % 60;
  const ampm = h24 < 12 ? 'AM' : 'PM';
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  const mm = minute.toString().padStart(2, '0');
  return `${h12}:${mm} ${ampm}`;
}

export function weekdayKeyFromIso(dateIso: string): WeekdayKey {
  const [y, m, d] = dateIso.split('-').map(Number);
  if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return 'monday';
  const dt = new Date(y, m - 1, d);
  const mon0 = (dt.getDay() + 6) % 7;
  return WEEKDAY_KEYS[mon0];
}

export function defaultWeeklyAvailability(): WeeklyAvailability {
  const out = {} as WeeklyAvailability;
  for (const k of WEEKDAY_KEYS) {
    if (k === 'saturday' || k === 'sunday') {
      out[k] = { enabled: false, start: '09:00', end: '17:00' };
    } else {
      out[k] = { enabled: true, start: '09:00', end: '17:00' };
    }
  }
  return out;
}

function isCompleteWeekly(raw: unknown): raw is Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return false;
  return WEEKDAY_KEYS.every((k) => {
    const v = (raw as Record<string, unknown>)[k];
    return v && typeof v === 'object' && !Array.isArray(v);
  });
}

export function normalizeWeeklyAvailability(raw: unknown): WeeklyAvailability {
  const src = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {};
  const out = {} as WeeklyAvailability;
  for (const k of WEEKDAY_KEYS) {
    const seg = src[k];
    const o = seg && typeof seg === 'object' && !Array.isArray(seg) ? (seg as Record<string, unknown>) : {};
    const enabled = Boolean(o.enabled ?? true);
    const start = String(o.start ?? '09:00').trim() || '09:00';
    const end = String(o.end ?? '17:00').trim() || '17:00';
    out[k] = { enabled, start, end };
  }
  return out;
}

function weeklyFromLegacyWindow(workingHours: unknown): WeeklyAvailability {
  const { startMin, endMin } = dailyWindowMinutesFromWorkingHours(workingHours);
  const pad = (n: number) => n.toString().padStart(2, '0');
  const start = `${pad(Math.floor(startMin / 60))}:${pad(startMin % 60)}`;
  const end = `${pad(Math.floor(endMin / 60))}:${pad(endMin % 60)}`;
  const out = {} as WeeklyAvailability;
  for (const k of WEEKDAY_KEYS) {
    out[k] = { enabled: true, start, end };
  }
  return out;
}

export function effectiveWeeklyAvailability(weekly: unknown, workingHours: unknown): WeeklyAvailability {
  if (isCompleteWeekly(weekly)) return normalizeWeeklyAvailability(weekly);
  if (
    workingHours &&
    typeof workingHours === 'object' &&
    !Array.isArray(workingHours) &&
    (workingHours as Record<string, unknown>).window
  ) {
    return weeklyFromLegacyWindow(workingHours);
  }
  return defaultWeeklyAvailability();
}

export function isDateBlocked(blockedDates: unknown, dateIso: string): boolean {
  if (!Array.isArray(blockedDates)) return false;
  const needle = dateIso.trim();
  return blockedDates.some((x) => String(x).trim() === needle);
}

export function normalizeBlockedDatesList(raw: unknown, max = 200): string[] {
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const x of raw) {
    const s = String(x).trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
    if (out.length >= max) break;
  }
  out.sort();
  return out;
}

export function minutesWindowForDate(
  weeklyEff: WeeklyAvailability,
  dateIso: string
): { startMin: number; endMin: number } | null {
  const key = weekdayKeyFromIso(dateIso);
  const day = weeklyEff[key];
  if (!day.enabled) return null;
  const sm = parseHourMinuteToMinutes(day.start);
  const em = parseHourMinuteToMinutes(day.end);
  if (sm == null || em == null || em <= sm) return null;
  return { startMin: sm, endMin: em };
}

/**
 * 12h slot labels for a calendar day (tenant-local date string YYYY-MM-DD).
 */
export function buildBookingDaySlots(
  slotDurationMinutes: number,
  weeklyAvailability: unknown,
  workingHours: unknown,
  blockedDates: unknown,
  dateIso: string
): string[] {
  if (isDateBlocked(blockedDates, dateIso)) return [];
  const dur = Math.max(1, Math.floor(Number(slotDurationMinutes)) || 30);
  const weekly = effectiveWeeklyAvailability(weeklyAvailability, workingHours);
  const win = minutesWindowForDate(weekly, dateIso);
  if (!win) return [];
  const out: string[] = [];
  for (let m = win.startMin; m < win.endMin; m += dur) {
    out.push(format12FromMinutes(m));
  }
  return out;
}

export function isCalendarDateUnavailable(
  weeklyAvailability: unknown,
  workingHours: unknown,
  blockedDates: unknown,
  dateIso: string
): boolean {
  if (isDateBlocked(blockedDates, dateIso)) return true;
  const weekly = effectiveWeeklyAvailability(weeklyAvailability, workingHours);
  return minutesWindowForDate(weekly, dateIso) == null;
}
