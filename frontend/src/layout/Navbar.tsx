import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LogOut, Menu, Moon, Sun } from 'lucide-react';
import { cn } from '@/utils/cn';
import { useAuth } from '@/hooks/AuthContext';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/Button';

const navItems = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Booking', path: '/booking' },
  { name: 'Analytics', path: '/analytics' },
  { name: 'Billing', path: '/billing' },
  { name: 'Settings', path: '/settings' },
] as const;

export const Navbar: React.FC = () => {
  const { profile, logoutUser } = useAuth();
  const { theme, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/90">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6 lg:gap-10">
          <NavLink to="/dashboard" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 font-semibold text-white shadow-md shadow-blue-600/25">
              AR
            </span>
            <span className="hidden text-lg font-semibold tracking-tight text-slate-900 sm:inline dark:text-white">
              AI Receptionist
            </span>
          </NavLink>

          <nav className="hidden items-center gap-0.5 md:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/80 dark:text-blue-300'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-100'
                  )
                }
              >
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => setMobileOpen((s) => !s)}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden dark:text-slate-300 dark:hover:bg-slate-900"
            aria-label="Menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="hidden flex-col items-end text-right text-sm leading-tight sm:flex">
            <span className="font-medium text-slate-900 dark:text-slate-100">{profile?.name ?? 'Business'}</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">Profile</span>
          </div>

          <button
            type="button"
            onClick={toggle}
            className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <Button variant="outline" size="sm" onClick={logoutUser} className="hidden sm:inline-flex">
            <LogOut className="mr-1.5 h-4 w-4" />
            Logout
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-200 px-4 py-3 md:hidden dark:border-slate-800">
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'rounded-lg px-3 py-2 text-sm font-medium',
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                      : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-900'
                  )
                }
              >
                {item.name}
              </NavLink>
            ))}
            <Button variant="outline" size="sm" className="mt-2 justify-center" onClick={logoutUser}>
              <LogOut className="mr-1.5 h-4 w-4" />
              Logout
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
};
