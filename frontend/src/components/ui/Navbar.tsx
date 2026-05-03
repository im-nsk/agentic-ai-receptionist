import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from './Button';
import { LogOut, LayoutDashboard, Calendar, BarChart3, Receipt, Settings, User } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', icon: <LayoutDashboard size={18} />, path: '/dashboard' },
    { name: 'Booking', icon: <Calendar size={18} />, path: '/booking' },
    { name: 'Analytics', icon: <BarChart3 size={18} />, path: '/analytics' },
    { name: 'Billing', icon: <Receipt size={18} />, path: '/billing' },
    { name: 'Settings', icon: <Settings size={18} />, path: '/settings' },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full glass border-b border-white/20">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <div className="w-4 h-4 border-2 border-white rounded-full"></div>
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-800">
              AI Receptionist
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-white/50 text-blue-600 shadow-sm border border-white/50'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-white/30'
                  }`
                }
              >
                {item.icon}
                {item.name}
              </NavLink>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex flex-col items-end mr-2">
            <span className="text-sm font-bold text-slate-800 leading-tight">{user?.name || 'Receptionist'}</span>
            <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400">Administrator</span>
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout} className="glass text-slate-600 border-white/50 hover:bg-white/40">
            <LogOut size={16} />
            Logout
          </Button>
        </div>
      </div>
    </nav>
  );
};
