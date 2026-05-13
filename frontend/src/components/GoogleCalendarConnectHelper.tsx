import React, { useCallback, useState } from 'react';
import { ChevronDown, Copy, ExternalLink, Info } from 'lucide-react';
import { useToast } from '@/components/toast/ToastContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';

const GOOGLE_CALENDAR_ORIGIN = 'https://calendar.google.com/';

interface GoogleCalendarConnectHelperProps {
  serviceAccountEmail: string | null;
  configLoading: boolean;
  disabled?: boolean;
  defaultHowToOpen?: boolean;
}

export const GoogleCalendarConnectHelper: React.FC<GoogleCalendarConnectHelperProps> = ({
  serviceAccountEmail,
  configLoading,
  disabled,
  defaultHowToOpen = true,
}) => {
  const toast = useToast();
  const [howToOpen, setHowToOpen] = useState(defaultHowToOpen);

  const copyEmail = useCallback(async () => {
    if (!serviceAccountEmail) {
      toast.error('Service account email is not available yet.');
      return;
    }
    try {
      await navigator.clipboard.writeText(serviceAccountEmail);
      toast.success('Email copied to clipboard.');
    } catch {
      toast.error('Could not copy. Select the email and copy manually.');
    }
  }, [serviceAccountEmail, toast]);

  return (
    <div className="rounded-xl border border-slate-200/90 bg-gradient-to-b from-slate-50/90 to-white p-4 shadow-sm dark:border-slate-700 dark:from-slate-900/80 dark:to-slate-950 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-slate-900 dark:text-slate-50">Connect Google Calendar</h4>
            <button
              type="button"
              className="inline-flex cursor-help rounded-lg p-1 text-slate-400 outline-none ring-blue-600/30 hover:bg-slate-100 hover:text-slate-600 focus-visible:ring-2 dark:hover:bg-slate-800 dark:hover:text-slate-300"
              title="We use a secure Google service account (not OAuth). You add our system email in Google Calendar sharing so we can read busy times and create bookings."
              aria-label="We use a secure Google service account (not OAuth). You add our system email in Google Calendar sharing so we can read busy times and create bookings."
            >
              <Info className="h-4 w-4 shrink-0" aria-hidden />
            </button>
          </div>
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            To allow AI booking automation, share your Google Calendar with our secure booking service account.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 sm:justify-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={disabled}
            onClick={() => window.open(GOOGLE_CALENDAR_ORIGIN, '_blank', 'noopener,noreferrer')}
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            Open Google Calendar
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">Share your calendar with this email:</p>
        {configLoading ? (
          <div className="h-11 animate-pulse rounded-lg bg-slate-200/80 dark:bg-slate-800" aria-hidden />
        ) : serviceAccountEmail ? (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
            <div className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2.5 font-mono text-xs leading-relaxed text-slate-800 shadow-inner dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 sm:text-sm">
              {serviceAccountEmail}
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="shrink-0 gap-1.5 sm:self-center"
              disabled={disabled}
              onClick={() => void copyEmail()}
            >
              <Copy className="h-3.5 w-3.5" aria-hidden />
              Copy
            </Button>
          </div>
        ) : (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-100">
            The booking service account email is not configured on the server. Your administrator should set{' '}
            <span className="font-mono text-xs">GOOGLE_SERVICE_ACCOUNT_EMAIL</span> or valid{' '}
            <span className="font-mono text-xs">GOOGLE_CREDENTIALS_JSON</span>.
          </p>
        )}
      </div>

      <div className="mt-4 border-t border-slate-200/80 pt-3 dark:border-slate-700/80">
        <button
          type="button"
          onClick={() => setHowToOpen((o) => !o)}
          className="flex w-full items-center justify-between gap-2 rounded-lg px-1 py-2 text-left text-sm font-medium text-slate-800 hover:bg-slate-100/80 dark:text-slate-200 dark:hover:bg-slate-800/60"
          aria-expanded={howToOpen}
        >
          <span>How to connect?</span>
          <ChevronDown className={cn('h-4 w-4 shrink-0 text-slate-500 transition-transform', howToOpen && 'rotate-180')} aria-hidden />
        </button>
        {howToOpen && (
          <div className="mt-2 space-y-4 pl-0.5">
            <div>
              <p className="text-sm font-medium text-slate-800 dark:text-slate-200">In Google Calendar</p>
              <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-slate-700 dark:text-slate-300">
                <li>Open your calendar settings</li>
                <li>Select your calendar</li>
                <li>Open &quot;Shared with&quot;</li>
                <li>Add the email above</li>
                <li>
                  Give permission: <span className="font-medium">&quot;Make changes to events&quot;</span>
                </li>
              </ol>
            </div>
            <div>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
                Then enter your Google Calendar ID in the field below (usually the account that owns the calendar you shared).
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
