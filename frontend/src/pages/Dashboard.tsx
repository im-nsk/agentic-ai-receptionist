import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import { Calendar, Users, Target, Activity, Clock } from 'lucide-react';
import { motion } from 'motion/react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [clientInfo, setClientInfo] = useState<{ name: string; minutes_used: number; plan_limit: number } | null>(null);

  useEffect(() => {
    const fetchClientInfo = async () => {
      try {
        const response = await client.get('/client');
        setClientInfo(response.data);
      } catch (error) {
        console.error('Error fetching client info:', error);
      }
    };
    fetchClientInfo();
  }, []);

  const stats = [
    { title: "Minutes Used", value: clientInfo ? `${clientInfo.minutes_used}` : '...', icon: <Activity className="text-blue-600" />, change: clientInfo ? `of ${clientInfo.plan_limit}` : '', trend: 'neutral' },
    { title: "Today's Bookings", value: '12', icon: <Calendar className="text-blue-600" />, change: '+20%', trend: 'up' },
    { title: 'Upcoming Appointments', value: '48', icon: <Users className="text-purple-600" />, change: '+5%', trend: 'up' },
    { title: 'Success Rate', value: '98%', icon: <Target className="text-green-600" />, change: 'Optimal', trend: 'neutral' },
  ];

  const recentActivity = [
    { id: 1, action: 'Booking Confirmed', client: 'James Wilson', time: '10 mins ago', status: 'Success' },
    { id: 2, action: 'Appointment Rescheduled', client: 'Sarah Miller', time: '45 mins ago', status: 'Pending' },
    { id: 3, action: 'Inquiry Resolved', client: 'Robert Ford', time: '2 hours ago', status: 'Success' },
    { id: 4, action: 'New Booking Request', client: 'Emily Stone', time: '3 hours ago', status: 'Success' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Welcome Back, {user?.name || clientInfo?.name || 'Receptionist'}</h1>
          <p className="text-slate-500">Here's an overview of your business today.</p>
        </div>
        <div className="flex h-10 w-fit items-center gap-2 rounded-lg bg-white px-3 shadow-sm border border-slate-200">
           <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
           <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">AI Live Now</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <Card key={i} className="flex items-center space-x-4 p-5 hover:bg-white/40 transition-all group">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/50 border border-white/50 shadow-sm transition-transform group-hover:scale-110">
              {stat.icon}
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                {stat.title}
              </p>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-800">{stat.value}</span>
                <span className={`text-xs font-bold ${
                  stat.trend === 'up' ? 'text-emerald-500' : 
                  stat.trend === 'down' ? 'text-blue-500' : 'text-slate-400'
                }`}>
                  {stat.change}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Booking Trends" description="Weekly booking volume visualization">
          <div className="flex h-[300px] w-full flex-col items-center justify-center space-y-4 rounded-xl bg-white/20 border border-white/30 text-slate-300 font-bold text-sm">
            <Activity size={48} className="text-blue-200/50 mb-2" />
            <div className="flex items-end gap-2 h-32 w-full max-w-md px-4">
              {[40, 60, 85, 70, 50, 90, 45].map((h, i) => (
                <div key={i} className="w-full bg-blue-500/30 rounded-t-lg transition-all hover:bg-blue-600/50 cursor-pointer border border-white/20" style={{ height: `${h}%` }}></div>
              ))}
            </div>
            <div className="flex justify-between w-full max-w-md px-4 text-[10px] uppercase tracking-widest font-bold">
              <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
            </div>
          </div>
        </Card>

        <Card title="Today's Schedule" description="Your upcoming appointments for today.">
          <div className="space-y-4">
            {[1, 2, 3].map((_, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl border border-white/30 bg-white/20 p-3 hover:bg-white/40 transition-all cursor-pointer group">
                <div className="flex items-center gap-3">
                   <div className="h-10 w-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold border border-white/50 group-hover:rotate-6 transition-transform">
                      {['JM', 'SM', 'RF'][i]}
                   </div>
                   <div>
                     <p className="text-sm font-bold text-slate-800">{['James Miller', 'Sarah Stone', 'Ray Ford'][i]}</p>
                     <p className="text-[10px] font-bold text-slate-400 flex items-center gap-1 uppercase tracking-wider">
                        <Clock size={12} />
                        {[ '10:30 AM', '1:00 PM', '4:15 PM'][i]}
                     </p>
                   </div>
                </div>
                <div className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-emerald-100/50 text-emerald-700 border border-emerald-200/50">
                  Confirmed
                </div>
              </div>
            ))}
            <button className="w-full py-2.5 text-xs font-bold uppercase tracking-widest text-blue-600 hover:bg-white/40 rounded-xl transition-all border border-transparent hover:border-white/50">
               View Full Schedule
            </button>
          </div>
        </Card>
      </div>

      <Card title="Recent AI Activity" description="Log of the latest AI receptionist interactions.">
          <Table headers={['Event', 'Client', 'Time', 'Outcome']}>
            {recentActivity.map((act) => (
              <TableRow key={act.id}>
                <TableCell className="font-medium">{act.action}</TableCell>
                <TableCell>{act.client}</TableCell>
                <TableCell>{act.time}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                    act.status === 'Success' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {act.status}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </Table>
      </Card>
    </div>
  );
};
