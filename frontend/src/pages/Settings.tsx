import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { getClient, postSetup, type ClientResponse } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { useToast } from '@/components/toast/ToastContext';
import { useAuth } from '@/hooks/AuthContext';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { phoneFieldError } from '@/utils/phone';
import { COMMON_TIMEZONES, DEFAULT_TIMEZONE } from '@/utils/timezones';
import { dailyWindowMinutesFromWorkingHours, minutesToTimeInputValue } from '@/utils/slots';

function servicesToLines(services: string[]): string {
  return services.length ? services.join('\n') : '';
}

function workingHoursToSummary(wh: ClientResponse['working_hours']): string {
  if (wh == null || wh === '') return '';
  if (typeof wh === 'string') return wh.trim();
  if (typeof wh === 'object' && !Array.isArray(wh)) {
    const s = (wh as { summary?: unknown }).summary;
    if (typeof s === 'string') return s.trim();
    try {
      return JSON.stringify(wh);
    } catch {
      return '';
    }
  }
  return '';
}

function extractDayWindow(wh: ClientResponse['working_hours']): { start: string; end: string } {
  const { startMin, endMin } = dailyWindowMinutesFromWorkingHours(wh);
  return { start: minutesToTimeInputValue(startMin), end: minutesToTimeInputValue(endMin) };
}

function buildWorkingHoursForSave(summary: string, dayStart: string, dayEnd: string): Record<string, unknown> {
  const out: Record<string, unknown> = {
    window: {
      start: (dayStart || '09:00').trim() || '09:00',
      end: (dayEnd || '18:00').trim() || '18:00',
    },
  };
  const s = summary.trim();
  if (s) out.summary = s;
  return out;
}

export const Settings: React.FC = () => {
  const toast = useToast();
  const { refreshProfile } = useAuth();
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  const [calendarId, setCalendarId] = useState('');
  const [linkedSheetId, setLinkedSheetId] = useState('');
  const [timezone, setTimezone] = useState(DEFAULT_TIMEZONE);
  const [clientPhoneNumber, setClientPhoneNumber] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [workingHoursSummary, setWorkingHoursSummary] = useState('');
  const [dayWindowStart, setDayWindowStart] = useState('09:00');
  const [dayWindowEnd, setDayWindowEnd] = useState('18:00');
  const [slotDuration, setSlotDuration] = useState(30);
  const [servicesText, setServicesText] = useState('');
  const [freeText, setFreeText] = useState('');

  const [setupComplete, setSetupComplete] = useState(false);
  const [editing, setEditing] = useState(true);

  const [saving, setSaving] = useState(false);

  const applyClient = useCallback((c: ClientResponse) => {
    setCalendarId((c.calendar_id || '').trim());
    setLinkedSheetId((c.sheet_id || '').trim());
    setTimezone((c.timezone || '').trim() || DEFAULT_TIMEZONE);
    setClientPhoneNumber((c.client_phone || '').trim());
    setBusinessName((c.business_name || '').trim());
    setWorkingHoursSummary(workingHoursToSummary(c.working_hours));
    const dw = extractDayWindow(c.working_hours);
    setDayWindowStart(dw.start);
    setDayWindowEnd(dw.end);
    setSlotDuration(typeof c.slot_duration === 'number' && c.slot_duration > 0 ? c.slot_duration : 30);
    setServicesText(servicesToLines(c.services ?? []));
    setFreeText((c.free_text || '').trim());
    const done = Boolean(c.setup_complete);
    setSetupComplete(done);
    setEditing(!done);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    try {
      applyClient(await getClient());
    } catch (err) {
      setLoadFailed(true);
      setEditing(true);
      toast.error(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applyClient, toast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const parseServices = useMemo(() => {
    return servicesText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [servicesText]);

  const showForm = !setupComplete || editing;
  const collapsed = setupComplete && !editing && !loading;
  const inputDisabled = loading || (setupComplete && !editing) || saving;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const cal = calendarId.trim();
    const tz = timezone.trim();

    if (!cal || !tz) {
      toast.error('Calendar ID and timezone are required.');
      return;
    }
    if (!cal.includes('@')) {
      toast.error('Calendar ID must look like an email.');
      return;
    }
    const ownerPhone = clientPhoneNumber.trim();
    const phoneErr = phoneFieldError(ownerPhone);
    if (!ownerPhone || phoneErr) {
      toast.error(phoneErr || 'Enter a valid owner phone number.');
      return;
    }
    const toMin = (t: string) => {
      const p = t.trim().split(':');
      if (p.length < 2) return null;
      const h = parseInt(p[0], 10);
      const mm = parseInt(p[1], 10);
      if (Number.isNaN(h) || Number.isNaN(mm)) return null;
      return h * 60 + mm;
    };
    const ws = toMin(dayWindowStart);
    const we = toMin(dayWindowEnd);
    if (ws == null || we == null || we <= ws) {
      toast.error('Daily booking window end must be after start.');
      return;
    }
    try {
      setSaving(true);
      await postSetup({
        calendar_id: cal,
        timezone: tz,
        client_phone: ownerPhone,
        business_name: businessName.trim() || null,
        working_hours: buildWorkingHoursForSave(workingHoursSummary, dayWindowStart, dayWindowEnd),
        slot_duration: slotDuration,
        services: parseServices,
        free_text: freeText.trim() || null,
      });
      toast.success('Settings saved.');
      setSetupComplete(true);
      setEditing(false);
      await refresh();
      await refreshProfile();
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Settings</h1>
        <p className="text-slate-500 dark:text-slate-400">
          {collapsed ? 'Your workspace is connected and ready.' : 'Connect Google services and tune how your assistant represents your business.'}
        </p>
      </div>

      {loadFailed && (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Couldn&apos;t load settings.{' '}
          <button type="button" onClick={() => void refresh()} className="font-medium text-blue-600 underline hover:text-blue-500">
            Retry
          </button>
        </p>
      )}

      {loading && (
        <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-16 dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-col items-center gap-3">
            <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-blue-600 border-t-transparent" />
            <p className="text-sm text-slate-500 dark:text-slate-400">Loading settings…</p>
          </div>
        </div>
      )}

      {!loading && collapsed && (
        <Card className="border-emerald-200/80 bg-gradient-to-br from-emerald-50 to-white shadow-sm dark:border-emerald-900/50 dark:from-emerald-950/40 dark:to-slate-950">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-base font-semibold text-emerald-950 dark:text-emerald-50">Google Calendar and Booking Sheet connected</p>
              <p className="mt-1 text-sm text-emerald-900/90 dark:text-emerald-100/90">
                Availability uses your calendar; bookings are logged to your Google Sheet. AI phone numbers are managed in the backend.
              </p>
            </div>
            <Button type="button" variant="outline" size="sm" className="shrink-0 self-start sm:self-center" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </div>
        </Card>
      )}

      {!loading && showForm && (
        <form onSubmit={handleSave} className="space-y-8">
          {setupComplete && editing && (
            <Card className="border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
              <p className="text-sm text-slate-700 dark:text-slate-300">
                You&apos;re editing integration details. Save to apply changes and return to the summary view.
              </p>
            </Card>
          )}

          <Card
            title="Integrations"
            description="Google Calendar for availability. A booking spreadsheet is created for you automatically (or use an existing linked sheet from a prior setup)."
          >
            <div className="space-y-5 pt-2">
              <Input
                label="Google Calendar ID"
                value={calendarId}
                onChange={(e) => setCalendarId(e.target.value)}
                placeholder="owner@business.com"
                disabled={inputDisabled}
                required
              />
              {linkedSheetId ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-700 dark:bg-slate-900/50">
                  <p className="font-medium text-slate-800 dark:text-slate-100">Booking spreadsheet</p>
                  <p className="mt-1 break-all text-slate-600 dark:text-slate-400">
                    <a
                      href={`https://docs.google.com/spreadsheets/d/${linkedSheetId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline hover:text-blue-500 dark:text-blue-400"
                    >
                      Open in Google Sheets
                    </a>
                  </p>
                </div>
              ) : (
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  After you save, we&apos;ll create a Google Sheet with the correct columns and freeze the header row.
                </p>
              )}
              <Select label="Timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} disabled={inputDisabled} required>
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </Select>
              <Input
                label="Owner personal / contact number"
                placeholder="+1 ..."
                value={clientPhoneNumber}
                onChange={(e) => setClientPhoneNumber(e.target.value)}
                disabled={inputDisabled}
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Your direct line for notifications; separate from the AI line used for inbound webhooks.
              </p>
            </div>
          </Card>

          <Card title="Business profile" description="How your assistant describes offerings and hours">
            <div className="space-y-5 pt-2">
              <Input
                label="Business name"
                placeholder="Displayed when useful for callers"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                disabled={inputDisabled}
              />
              <Input
                label="Working hours (summary)"
                placeholder="Mon–Fri 9am–6pm EST"
                value={workingHoursSummary}
                onChange={(e) => setWorkingHoursSummary(e.target.value)}
                disabled={inputDisabled}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="day-window-start">
                    Daily booking window (start)
                  </label>
                  <input
                    id="day-window-start"
                    type="time"
                    step={60}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:pointer-events-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
                    value={dayWindowStart}
                    onChange={(e) => setDayWindowStart(e.target.value)}
                    disabled={inputDisabled}
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="day-window-end">
                    Daily booking window (end)
                  </label>
                  <input
                    id="day-window-end"
                    type="time"
                    step={60}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:pointer-events-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
                    value={dayWindowEnd}
                    onChange={(e) => setDayWindowEnd(e.target.value)}
                    disabled={inputDisabled}
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                The public Booking page lists times inside this window, spaced by slot duration. The end time is exclusive (18:00 means slots only before 6:00 PM).
              </p>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="slot-duration-input">
                  Slot duration (minutes)
                </label>
                <input
                  id="slot-duration-input"
                  type="number"
                  min={15}
                  max={480}
                  step={5}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:pointer-events-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
                  value={slotDuration}
                  onChange={(e) => setSlotDuration(Number(e.target.value) || 30)}
                  disabled={inputDisabled}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="services-text">
                  Services / offerings (one per line or comma-separated)
                </label>
                <textarea
                  id="services-text"
                  rows={4}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:pointer-events-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
                  value={servicesText}
                  onChange={(e) => setServicesText(e.target.value)}
                  disabled={inputDisabled}
                  placeholder="Haircut&#10;Color treatment"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-slate-50" htmlFor="free-text">
                  Free-form notes for the assistant
                </label>
                <textarea
                  id="free-text"
                  rows={5}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:pointer-events-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-50"
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  disabled={inputDisabled}
                  placeholder="Parking instructions, FAQs, pronunciation…"
                />
              </div>
            </div>
          </Card>

          <Card title="About your data">
            <ul className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
              <li>Your booking log lives in Google Sheets (created automatically on first save). Headers stay consistent; you can edit data rows safely.</li>
              <li>Dashboard metrics are read from the server, not your browser.</li>
            </ul>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button type="submit" className="w-full sm:w-auto" isLoading={saving} disabled={loading}>
              Save settings
            </Button>
            {setupComplete && editing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void (async () => {
                    try {
                      applyClient(await getClient());
                      setEditing(false);
                    } catch (err) {
                      toast.error(getApiErrorMessage(err));
                    }
                  })();
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      )}
    </div>
  );
};
