import React from 'react';
import { cn } from '@/utils/cn';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  description?: string;
}

export const Card: React.FC<CardProps> = ({ children, className, title, description }) => (
  <div
    className={cn(
      'rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm shadow-slate-200/50 dark:border-slate-800 dark:bg-slate-900/70 dark:shadow-black/40',
      className
    )}
  >
    {(title ?? description) && (
      <div className={cn(children ? 'mb-4' : '', 'space-y-1')}>
        {title && (
          <h3 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-50">{title}</h3>
        )}
        {description && <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>}
      </div>
    )}
    {children}
  </div>
);
