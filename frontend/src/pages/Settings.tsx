import React, { useState } from 'react';
import { postSetup } from '@/api/client';
import { getApiErrorMessage } from '@/api/errors';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { COMMON_TIMEZONES, DEFAULT_TIMEZONE } from '@/utils/timezones';

export const Settings: React.FC = () => {
  const [calendarId, setCalendarId] = useState('');
  const [sheetId, setSheetId] = useState('');
  const [timezone, setTimezone] = useState(DEFAULT_TIMEZONE);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    const cal = calendarId.trim();
    const sheet = sheetId.trim();
    if (!cal || !sheet) {
      setError('Calendar ID and Sheet ID are required.');
      return;
    }
    if (!cal.includes('@')) {
      setError('Calendar ID must match Google Calendar email format.');
      return;
    }
    if (sheet.length < 20) {
      setError('Paste the full Google Sheet ID.');
      return;
    }

    try {
      setSaving(true);
      await postSetup({
        calendar_id: cal,
        sheet_id: sheet,
        timezone,
      });
      setMessage('Setup saved successfully.');
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Settings</h1>
          <p className="text-slate-500 dark:text-slate-400">Manage bookings and availability in one place</p>
        </div>
      </div>

      <Card title="Setup" description="Collect setup inputs and send to backend /setup">
        <form onSubmit={handleSave} className="space-y-5 pt-2">
          <Input
            label="Google Calendar ID"
            value={calendarId}
            onChange={(e) => setCalendarId(e.target.value)}
            placeholder="owner@business.com"
          />
          <Input
            label="Google Sheet ID"
            value={sheetId}
            onChange={(e) => setSheetId(e.target.value)}
            placeholder="ID between spreadsheets/d/ and /edit"
          />
          <Select label="Timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </Select>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Configure Google Calendar and Sheets integration for booking automation.
          </p>
          {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
          {message && <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{message}</p>}
          <Button type="submit" className="w-full sm:w-auto" isLoading={saving}>
            Save setup
          </Button>
        </form>
      </Card>
    </div>
  );
};
