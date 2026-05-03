import React from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { CheckCircle2, CreditCard, Clock, Receipt } from 'lucide-react';

export const Billing: React.FC = () => {
  const currentUsage = {
    minutesUsed: 420,
    minuteLimit: 500,
    bookingsUsed: 124,
    bookingLimit: 150,
  };

  const planFeatures = [
    '24/7 AI Receptionist Availability',
    'Custom Voice Personality',
    'Google Calendar Integration',
    'Email & SMS Notifications',
    'Lead Qualification Forms',
    'Priority Phone Support'
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Billing & Subscription</h1>
          <p className="text-slate-500">Manage your plan and monitor resource usage.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Usage Progress - Column 1 & 2 */}
        <div className="lg:col-span-2 space-y-6">
          <Card title="Resource Usage" description="Your consumption for the current billing cycle.">
            <div className="space-y-8 pt-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-slate-700">AI Call Minutes</p>
                  <p className="text-sm font-bold text-slate-900">
                    {currentUsage.minutesUsed} / {currentUsage.minuteLimit} min
                  </p>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    className="h-full bg-blue-600 transition-all duration-1000" 
                    style={{ width: `${(currentUsage.minutesUsed / currentUsage.minuteLimit) * 100}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  You have used 84% of your monthly available call minutes.
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-slate-700">Booking Capacity</p>
                  <p className="text-sm font-bold text-slate-900">
                    {currentUsage.bookingsUsed} / {currentUsage.bookingLimit} records
                  </p>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div 
                    className="h-full bg-purple-600 transition-all duration-1000" 
                    style={{ width: `${(currentUsage.bookingsUsed / currentUsage.bookingLimit) * 100}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  Resets in 12 days (May 15, 2026).
                </p>
              </div>

              <div className="flex items-center gap-4 rounded-lg bg-blue-50 p-4 border border-blue-100">
                 <div className="h-10 w-10 flex items-center justify-center rounded-full bg-white shadow-sm text-blue-600">
                    <Receipt size={20} />
                 </div>
                 <div className="flex-1">
                   <p className="text-sm font-semibold text-blue-900">Need more minutes?</p>
                   <p className="text-xs text-blue-700">Upgrade your plan to get unlimited minutes and advanced AI models.</p>
                 </div>
                 <Button size="sm">Upgrade Now</Button>
              </div>
            </div>
          </Card>

          <Card title="Payment Method">
             <div className="flex items-center justify-between p-4 rounded-xl border border-slate-100 bg-slate-50">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-14 rounded-lg bg-slate-200 flex items-center justify-center text-slate-500 text-[10px] font-bold uppercase tracking-widest border border-slate-300">
                     Visa
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-900">•••• •••• •••• 4242</p>
                    <p className="text-xs text-slate-500">Expires 12/2026</p>
                  </div>
                </div>
                <Button variant="outline" size="sm">Update</Button>
             </div>
          </Card>
        </div>

        {/* Plan Details - Column 3 */}
        <Card className="h-fit" title="Your Plan" description="Currently on Professional Monthly">
           <div className="mb-6">
              <span className="text-4xl font-bold text-slate-900">$149</span>
              <span className="text-slate-500"> / month</span>
           </div>
           <div className="space-y-4 mb-8">
             {planFeatures.map((f, i) => (
               <div key={i} className="flex items-center gap-3 text-sm text-slate-600">
                 <CheckCircle2 size={16} className="text-blue-600 flex-shrink-0" />
                 {f}
               </div>
             ))}
           </div>
           <div className="space-y-3 pt-6 border-t border-slate-100">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <Clock size={14} />
                Next billing on May 15, 2026
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <CreditCard size={14} />
                Auto-renewal is enabled
              </div>
           </div>
        </Card>
      </div>
    </div>
  );
};
