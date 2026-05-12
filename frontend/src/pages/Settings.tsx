import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { getClient, postSetup, type ClientResponse } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { COMMON_TIMEZONES, DEFAULT_TIMEZONE } from '@/utils/timezones';

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

function summaryToWorkingHoursPayload(summary: string): Record<string, unknown> {
  const t = summary.trim();
  if (!t) return {};
  return { summary: t };
}

export const Settings: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [loadErr, setLoadErr] = useState('');

  const [calendarId, setCalendarId] = useState('');
  const [sheetId, setSheetId] = useState('');
  const [timezone, setTimezone] = useState(DEFAULT_TIMEZONE);
  const [clientPhoneNumber, setClientPhoneNumber] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [workingHoursSummary, setWorkingHoursSummary] = useState('');
  const [slotDuration, setSlotDuration] = useState(30);
  const [servicesText, setServicesText] = useState('');
  const [freeText, setFreeText] = useState('');

  const [setupComplete, setSetupComplete] = useState(false);
  const [editing, setEditing] = useState(true);

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const applyClient = useCallback((c: ClientResponse) => {
    setCalendarId((c.calendar_id || '').trim());
    setSheetId((c.sheet_id || '').trim());
    setTimezone((c.timezone || '').trim() || DEFAULT_TIMEZONE);
    setClientPhoneNumber((c.client_phone || '').trim());
    setBusinessName((c.business_name || '').trim());
    setWorkingHoursSummary(workingHoursToSummary(c.working_hours));
    setSlotDuration(typeof c.slot_duration === 'number' && c.slot_duration > 0 ? c.slot_duration : 30);
    setServicesText(servicesToLines(c.services ?? []));
    setFreeText((c.free_text || '').trim());
    const done = Boolean(c.setup_complete);
    setSetupComplete(done);
    setEditing(!done);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadErr('');
    try {
      applyClient(await getClient());
    } catch (err) {
      setLoadErr(getApiErrorMessage(err));
      setEditing(true);
    } finally {
      setLoading(false);
    }
  }, [applyClient]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const parseServices = useMemo(() => {
    return servicesText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [servicesText]);

  const locked = setupComplete && !editing && !loading;
  const inputDisabled = loading || locked || saving;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    const cal = calendarId.trim();
    const sheet = sheetId.trim();
    const tz = timezone.trim();

    if (!cal || !sheet || !tz) {
      setError('Calendar ID, Sheet ID, and timezone are required.');
      return;
    }
    if (!cal.includes('@')) {
      setError('Calendar ID must look like an email.');
      return;
    }
    if (sheet.length < 20) {
      setError('Paste the full Google Sheet ID.');
      return;
    }
    const ownerPhone = clientPhoneNumber.trim();
    if (!ownerPhone || ownerPhone.replace(/\D/g, '').length < 10) {
      setError('Owner / personal mobile needs 10+ digits for notifications and CRM-style records.');
      return;
    }
    try {
      setSaving(true);
      await postSetup({
        calendar_id: cal,
        sheet_id: sheet,
        timezone: tz,
        client_phone: ownerPhone,
        business_name: businessName.trim() || null,
        working_hours: summaryToWorkingHoursPayload(workingHoursSummary),
        slot_duration: slotDuration,
        services: parseServices,
        free_text: freeText.trim() || null,
      });
      setMessage('Settings saved.');
      setSetupComplete(true);
      setEditing(false);
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Settings</h1>
        <p className="text-slate-500 dark:text-slate-400">Configure integrations and how your assistant describes your business</p>
      </div>

      {loadErr && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/35 dark:text-amber-50">
          {loadErr}{' '}
          <button type="button" onClick={() => void refresh()} className="underline">
            Retry
          </button>
        </p>
      )}

      {setupComplete && !editing && !loading && (
        <Card className="border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-medium text-emerald-900 dark:text-emerald-100">Connected — Calendar and Sheet are configured</p>
            <Button type="button" variant="outline" size="sm" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </div>
        </Card>
      )}

      <form onSubmit={handleSave} className="space-y-8">
        <Card title="Integrations" description="Google Calendar and Sheets (audit trail). AI inbound numbers are provisioned in your backend (Twilio / VAPI).">
          <div className="space-y-5 pt-2">
            <Input
              label="Google Calendar ID"
              value={calendarId}
              onChange={(e) => setCalendarId(e.target.value)}
              placeholder="owner@business.com"
              disabled={inputDisabled}
              required
            />
            <Input
              label="Google Sheet ID"
              value={sheetId}
              onChange={(e) => setSheetId(e.target.value)}
              placeholder="ID between spreadsheets/d/ and /edit"
              disabled={inputDisabled}
              required
            />
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
              Your direct line for notifications; separate from the AI line configured for webhooks.
            </p>
          </div>
        </Card>

        <Card title="Business profile" description="Structured fields plus free-text prompts for assistants">
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

        <Card title="Data source">
          <ul className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
            <li>Google Calendar owns availability queries and finalized appointment events.</li>
            <li>Google Sheets stores a searchable booking log wired to your sheet integration.</li>
            <li>Dashboard and analytics load booking history from the server only (no browser cache).</li>
          </ul>
        </Card>

        {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
        {message && <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{message}</p>}

        <Button type="submit" className="w-full sm:w-auto" isLoading={saving} disabled={locked || loading}>
          Save settings
        </Button>
      </form>
    </div>
  );
};
