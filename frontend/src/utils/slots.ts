const HH_MM = /^([01]?\d|2[0-3]):([0-5]\d)$/;

/** Minutes from midnight for daily window; half-open [startMin, endMin). Defaults 9:00–18:00. */
export function dailyWindowMinutesFromWorkingHours(wh: unknown): { startMin: number; endMin: number } {
  const def = { startMin: 9 * 60, endMin: 18 * 60 };
  if (!wh || typeof wh !== 'object' || Array.isArray(wh)) return def;
  const win = (wh as Record<string, unknown>).window;
  if (!win || typeof win !== 'object' || Array.isArray(win)) return def;
  const startStr = String((win as Record<string, unknown>).start ?? '').trim();
  const endStr = String((win as Record<string, unknown>).end ?? '').trim();
  const sm = parseHourMinuteToMinutes(startStr);
  const em = parseHourMinuteToMinutes(endStr);
  if (sm == null || em == null || em <= sm) return def;
  return { startMin: sm, endMin: em };
}

function parseHourMinuteToMinutes(s: string): number | null {
  const m = s.match(HH_MM);
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

export function minutesToTimeInputValue(totalMinutes: number): string {
  const m = ((totalMinutes % (24 * 60)) + 24 * 60) % (24 * 60);
  const h = Math.floor(m / 60);
  const min = m % 60;
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
}

/**
 * 12-hour slot labels (e.g. "9:15 AM") from tenant slot_duration and working_hours.window.
 */
export function buildBookingDaySlots(slotDurationMinutes: number, workingHours: unknown): string[] {
  const dur = Math.max(1, Math.floor(Number(slotDurationMinutes)) || 30);
  const { startMin, endMin } = dailyWindowMinutesFromWorkingHours(workingHours);
  const out: string[] = [];
  for (let m = startMin; m < endMin; m += dur) {
    out.push(format12FromMinutes(m));
  }
  return out;
}
