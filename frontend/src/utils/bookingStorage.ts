const KEY = 'aireceptionist_recent_bookings';
const MAX = 30;

export interface StoredBooking {
  id: string;
  name: string;
  phone: string;
  date: string;
  time: string;
  status: 'confirmed' | 'failed';
  createdAt: number;
}

function load(): StoredBooking[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredBooking[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function save(items: StoredBooking[]) {
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
}

export function addStoredBooking(entry: Omit<StoredBooking, 'id' | 'createdAt'>) {
  const prev = load();
  const row: StoredBooking = {
    ...entry,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt: Date.now(),
  };
  save([row, ...prev]);
}

export function getStoredBookings(): StoredBooking[] {
  return load().sort((a, b) => b.createdAt - a.createdAt);
}

export function toISODateLocal(date: Date): string {
  const y = date.getFullYear();
  const m = `${date.getMonth() + 1}`.padStart(2, '0');
  const d = `${date.getDate()}`.padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function aggregateLast7DayCounts(): number[] {
  const items = load();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const counts = [0, 0, 0, 0, 0, 0, 0];

  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = new Date(today);
    day.setDate(today.getDate() - offset);
    const iso = toISODateLocal(day);
    counts[6 - offset] = items.filter((b) => b.date === iso && b.status === 'confirmed').length;
  }

  return counts;
}

export function sumConfirmedBookings(): number {
  return load().filter((b) => b.status === 'confirmed').length;
}

export function successRateFromStored(): number | null {
  const all = load();
  if (all.length === 0) return null;
  const confirmed = all.filter((b) => b.status === 'confirmed').length;
  return Math.round((confirmed / all.length) * 1000) / 10;
}
