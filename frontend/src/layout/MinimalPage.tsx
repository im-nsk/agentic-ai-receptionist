import React from 'react';

interface MinimalPageProps {
  children: React.ReactNode;
}

export const MinimalPage: React.FC<MinimalPageProps> = ({ children }) => (
  <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 px-4 dark:from-slate-950 dark:to-slate-900">
    {children}
  </div>
);
