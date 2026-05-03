import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';

export const MainLayout: React.FC = () => (
  <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
    <Navbar />
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Outlet />
    </main>
  </div>
);
