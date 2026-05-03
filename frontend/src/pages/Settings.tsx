import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Save, Calendar, Database, ShieldCheck, CheckCircle2, HelpCircle } from 'lucide-react';
import client from '../api/client';
import { cn } from '../lib/utils';

export const Settings: React.FC = () => {
  const [businessName, setBusinessName] = useState('Acme Medical Clinic');
  const [calendarId, setCalendarId] = useState('primary');
  const [sheetId, setSheetId] = useState('1aBc2D3eFgHiJkLmNoPqRsTuVwXyZ');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      await client.post('/setup', { 
        calendar_id: calendarId, 
        sheet_id: sheetId 
      });
      setMessage({ type: 'success', text: 'Settings saved successfully' });
    } catch (error) {
      console.error('Save failed:', error);
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Integration Settings</h1>
          <p className="text-slate-500">Connect your tools to power your AI Receptionist.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card title="Business Identity">
             <div className="space-y-4 pt-2">
               <Input 
                 label="Business Display Name" 
                 value={businessName} 
                 onChange={(e) => setBusinessName(e.target.value)}
                 id="business-name"
               />
               <p className="text-xs text-slate-500 italic">
                 "Hello! Welcome to {businessName || '[Business Name]'}. How can I assist you today?"
               </p>
             </div>
          </Card>

          <Card title="Integrations" description="Configure where your data and appointments are stored.">
             <div className="space-y-6 pt-4">
               <div className="space-y-4">
                 <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                       <Calendar size={18} className="text-blue-600" />
                       <span className="text-sm font-semibold text-slate-700">Google Calendar</span>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700 uppercase">
                      <CheckCircle2 size={10} />
                      Connected
                    </div>
                 </div>
                 <Input 
                   label="Calendar ID" 
                   value={calendarId} 
                   onChange={(e) => setCalendarId(e.target.value)} 
                   placeholder="e.g. primary or your-email@gmail.com"
                 />
               </div>

               <div className="space-y-4 pt-4 border-t border-slate-100">
                 <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                       <Database size={18} className="text-green-600" />
                       <span className="text-sm font-semibold text-slate-700">Google Sheets Dashboard</span>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700 uppercase">
                      <CheckCircle2 size={10} />
                      Connected
                    </div>
                 </div>
                 <Input 
                   label="Google Sheet ID" 
                   value={sheetId} 
                   onChange={(e) => setSheetId(e.target.value)}
                   placeholder="Paste your Sheet ID here"
                 />
               </div>
             </div>
          </Card>

          <Card title="Security & Privacy">
             <div className="space-y-4 pt-2">
               <div className="flex items-center justify-between p-4 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-3">
                     <ShieldCheck size={20} className="text-blue-600" />
                     <div>
                       <p className="text-sm font-semibold">2FA Authentication</p>
                       <p className="text-xs text-slate-500">Improve your account security</p>
                     </div>
                  </div>
                  <Button variant="outline" size="sm">Enable</Button>
               </div>
             </div>
          </Card>

          <div className="flex flex-col items-end gap-2">
            {message && (
              <p className={cn(
                "text-sm font-medium",
                message.type === 'success' ? "text-emerald-600" : "text-red-500"
              )}>
                {message.text}
              </p>
            )}
            <Button className="w-full sm:w-auto flex items-center gap-2" onClick={handleSave} isLoading={isLoading}>
              <Save size={18} />
              Save Settings
            </Button>
          </div>
        </div>

        <div className="space-y-6">
           <Card className="bg-slate-900 border-slate-900" title={<span className="text-white">Need Help?</span>}>
              <p className="text-sm text-slate-400 mb-6 leading-relaxed">
                Finding your Google IDs can be tricky. Check our visual guide to set up your integrations in minutes.
              </p>
              <Button variant="secondary" className="w-full flex items-center gap-2">
                <HelpCircle size={16} />
                Open Setup Guide
              </Button>
           </Card>

           <Card title="AI Status">
              <div className="space-y-4">
                 <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Sync Status</span>
                    <span className="text-sm font-bold text-green-600">In Real-time</span>
                 </div>
                 <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Last Synced</span>
                    <span className="text-sm font-medium text-slate-500">2 mins ago</span>
                 </div>
                 <Button variant="outline" className="w-full text-xs">Force Resync AI Data</Button>
              </div>
           </Card>
        </div>
      </div>
    </div>
  );
};
