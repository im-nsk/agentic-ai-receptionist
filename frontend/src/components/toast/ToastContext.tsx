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
  switch (variant) {
    case 'success':
      return 'border-emerald-200/90 bg-white text-emerald-950 shadow-emerald-900/10 dark:border-emerald-800/80 dark:bg-slate-900 dark:text-emerald-50';
    case 'error':
      return 'border-red-200/90 bg-white text-red-950 shadow-red-900/10 dark:border-red-900/60 dark:bg-slate-900 dark:text-red-100';
    default:
      return 'border-slate-200/90 bg-white text-slate-900 shadow-slate-900/10 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50';
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
        className="pointer-events-none fixed right-4 top-4 z-[200] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              'toast-animate pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm font-medium shadow-lg',
              variantStyles(t.variant)
            )}
          >
            <p className="min-w-0 flex-1 leading-snug">{t.message}</p>
            <button
              type="button"
              onClick={() => remove(t.id)}
              className="shrink-0 rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
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
