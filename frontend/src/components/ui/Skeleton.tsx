import React from 'react';
import { cn } from '@/utils/cn';

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-lg bg-slate-200/90 dark:bg-slate-700/80', className)} aria-hidden />;
}

export function StatCardSkeleton() {
  return (
    <div className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
      <Skeleton className="h-11 w-11 shrink-0 rounded-xl" />
      <div className="min-w-0 flex-1 space-y-2 pt-0.5">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-16 max-w-full" />
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="flex h-48 items-end gap-2 border-t border-slate-100 pt-6 dark:border-slate-800">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="flex flex-1 flex-col items-center gap-2">
          <Skeleton className="h-24 w-full max-w-[2.5rem] rounded-lg" />
          <Skeleton className="h-3 w-8" />
        </div>
      ))}
    </div>
  );
}
