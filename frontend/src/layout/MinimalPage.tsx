import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/theme/ThemeProvider';

interface MinimalPageProps {
  children: React.ReactNode;
}

export const MinimalPage: React.FC<MinimalPageProps> = ({ children }) => {
  const { theme, toggle } = useTheme();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 px-4 dark:from-slate-950 dark:to-slate-900">
      <button
        type="button"
        onClick={toggle}
        className="absolute right-4 top-4 rounded-lg border border-slate-200 bg-white/90 p-2 text-slate-600 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        aria-label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
      {children}
    </div>
  );
};
