import React from 'react';
import { cn } from '@/utils/cn';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  className,
  label,
  error,
  id,
  ...props
}) => {
  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          'flex h-11 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/35 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:focus-visible:ring-offset-slate-950',
          error && 'border-red-400 focus-visible:ring-red-400',
          error && 'dark:border-red-500/60',
          className
        )}
        {...props}
      />
      {error && <p className="text-xs font-medium text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
};
