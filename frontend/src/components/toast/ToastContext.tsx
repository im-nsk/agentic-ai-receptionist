import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/utils/cn';

export type ToastVariant = 'success' | 'error' | 'info';

type ToastItem = { id: number; message: string; variant: ToastVariant };

type ToastApi = {
  showToast: (message: string, variant?: ToastVariant) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

const ToastContext = createContext<ToastApi | null>(null);

const TOAST_MS = 5000;

function variantStyles(variant: ToastVariant): string {
  const shell =
    'border shadow-xl ring-1 ring-black/5 dark:ring-black/10 ' +
    'bg-slate-900 text-slate-50 border-slate-600/90 ' +
    'dark:bg-zinc-100 dark:text-zinc-900 dark:border-zinc-300/95';
  switch (variant) {
    case 'success':
      return cn(
        shell,
        'ring-emerald-500/25 dark:ring-emerald-600/15 border-emerald-700/40 dark:border-emerald-500/35'
      );
    case 'error':
      return cn(
        shell,
        'ring-red-500/25 dark:ring-red-600/12 border-red-700/45 dark:border-red-400/40'
      );
    default:
      return cn(
        shell,
        'ring-blue-500/20 dark:ring-blue-600/12 border-slate-500/50 dark:border-zinc-400/80'
      );
  }
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<number, number>>(new Map());

  const remove = useCallback((id: number) => {
    const t = timers.current.get(id);
    if (t != null) window.clearTimeout(t);
    timers.current.delete(id);
    setToasts((list) => list.filter((x) => x.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((list) => [...list, { id, message, variant }]);
      const handle = window.setTimeout(() => remove(id), TOAST_MS);
      timers.current.set(id, handle);
    },
    [remove]
  );

  const api = useMemo<ToastApi>(
    () => ({
      showToast,
      success: (m) => showToast(m, 'success'),
      error: (m) => showToast(m, 'error'),
      info: (m) => showToast(m, 'info'),
    }),
    [showToast]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed right-4 top-[4.75rem] z-[200] flex w-[min(28rem,calc(100vw-2rem))] flex-col gap-3 sm:right-6 sm:top-[4.75rem]"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              'toast-animate pointer-events-auto flex items-start gap-3.5 rounded-xl px-5 py-4 text-base font-medium leading-snug shadow-2xl',
              variantStyles(t.variant)
            )}
          >
            <p className="min-w-0 flex-1">{t.message}</p>
            <button
              type="button"
              onClick={() => remove(t.id)}
              className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-slate-100 dark:text-zinc-500 dark:hover:bg-black/[0.06] dark:hover:text-zinc-900"
              aria-label="Dismiss"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
