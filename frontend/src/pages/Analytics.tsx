import React from 'react';
import { Card } from '../components/ui/Card';
import { BarChart3, TrendingUp, Users, Target } from 'lucide-react';

export const Analytics: React.FC = () => {
  const kpis = [
    { title: 'Total Bookings', value: '1,284', icon: <BarChart3 className="text-blue-600" />, delta: '+12% vs last month', pos: true },
    { title: 'Success Rate', value: '98.2%', icon: <Target className="text-green-600" />, delta: 'High performance', pos: true },
    { title: 'New Leads', value: '432', icon: <Users className="text-purple-600" />, delta: '+5% growth', pos: true },
    { title: 'Conversion Rate', value: '15.4%', icon: <TrendingUp className="text-orange-600" />, delta: '+2.1% improvement', pos: true },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics Overview</h1>
          <p className="text-slate-500">Performance insights for your AI Receptionist.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi, i) => (
          <Card key={i} className="space-y-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-50">
              {kpi.icon}
            </div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{kpi.title}</p>
            <h3 className="text-2xl font-bold text-slate-900">{kpi.value}</h3>
            <p className={`text-xs font-medium ${kpi.pos ? 'text-green-600' : 'text-red-600'}`}>
              {kpi.delta}
            </p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Traffic & Trends" description="Daily booking engagement over the last 30 days">
           <div className="flex h-[320px] w-full flex-col items-center justify-center space-y-4 rounded-lg bg-slate-50/50 border border-dashed border-slate-200 uppercase tracking-widest text-slate-400 font-medium text-sm">
            <BarChart3 size={48} className="text-slate-200 mb-2" />
            [ Multi-series Chart Placeholder ]
          </div>
        </Card>
        
        <Card title="Customer Satisfaction" description="Post-booking feedback summary">
           <div className="flex h-[320px] w-full flex-col items-center justify-center space-y-4 rounded-lg bg-slate-50/50 border border-dashed border-slate-200 uppercase tracking-widest text-slate-400 font-medium text-sm">
            <Target size={48} className="text-slate-200 mb-2" />
            [ Pie Chart Placeholder ]
          </div>
        </Card>
      </div>
    </div>
  );
};
