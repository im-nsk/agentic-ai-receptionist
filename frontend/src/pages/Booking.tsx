import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Table, TableRow, TableCell } from '../components/ui/Table';
import { Calendar as CalendarIcon, Download, Search, CheckCircle2, XCircle, Clock } from 'lucide-react';
import client from '../api/client';
import { cn } from '../lib/utils';

export const Booking: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'schedule' | 'records'>('schedule');
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerName || !phoneNumber || !selectedDate || !selectedTime) {
      setMessage({ type: 'error', text: 'Please fill in all fields' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    const payload = {
      date: selectedDate,
      time: selectedTime,
      name: customerName,
      phone: phoneNumber
    };

    try {
      // First check availability
      const availRes = await client.post('/check-availability', payload);
      
      if (availRes.status === 200) {
        // Now book
        await client.post('/book-appointment', payload);
        setMessage({ type: 'success', text: 'Appointment booked successfully!' });
        setCustomerName('');
        setPhoneNumber('');
        setSelectedTime(null);
      }
    } catch (error: any) {
      console.error('Booking error:', error);
      const errorMsg = error.response?.data?.message || 'Failed to book appointment. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setIsLoading(false);
    }
  };

  const timeSlots = [
    '09:00 AM', '09:30 AM', '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM',
    '01:00 PM', '01:30 PM', '02:00 PM', '02:30 PM', '03:00 PM', '03:30 PM'
  ];

  const bookingRecords = [
    { name: 'Sarah Jenkins', phone: '+1 234 567 8901', date: '2023-10-24', time: '10:30 AM', status: 'Confirmed' },
    { name: 'Michael Thorne', phone: '+1 234 567 8902', date: '2023-10-23', time: '02:15 PM', status: 'Completed' },
    { name: 'Alisa Vohra', phone: '+1 234 567 8903', date: '2023-10-23', time: '09:00 AM', status: 'Confirmed' },
    { name: 'Gregory House', phone: '+1 234 567 8904', date: '2023-10-22', time: '04:45 PM', status: 'Cancelled' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Booking Management</h1>
          <p className="text-slate-500">Organize and track all incoming appointments.</p>
        </div>
        <div className="inline-flex rounded-xl bg-white/30 p-1 border border-white/20 glass">
          <button
            onClick={() => setActiveTab('schedule')}
            className={`rounded-lg px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all ${
              activeTab === 'schedule' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Schedule
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`rounded-lg px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all ${
              activeTab === 'records' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Records
          </button>
        </div>
      </div>

      {activeTab === 'schedule' ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Calendar Picker (Simple Placeholder representation) */}
          <Card className="lg:col-span-7" title="Select Date">
             <div className="grid grid-cols-7 gap-2 text-center mb-4">
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map(d => (
                  <div key={d} className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{d}</div>
                ))}
             </div>
             <div className="grid grid-cols-7 gap-2">
                {Array.from({ length: 31 }).map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedDate(`2023-10-${i+1}`)}
                    className={`h-10 rounded-xl text-sm font-bold transition-all border ${
                      i + 1 === 24 
                        ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-200' 
                        : 'bg-white/40 border-white/40 text-slate-600 hover:bg-white/80'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
             </div>
             <div className="mt-8 pt-8 border-t border-white/20">
               <div className="flex items-center gap-2 text-slate-500">
                 <CalendarIcon size={18} className="text-blue-600" />
                 <span className="text-xs font-bold uppercase tracking-wider">Selected Date:</span>
                 <span className="text-sm font-bold text-slate-800">October 24, 2023</span>
               </div>
             </div>
          </Card>

          {/* Time & Booking Section */}
          <div className="lg:col-span-5 space-y-6">
            <Card title="Available Time Slots">
              <div className="grid grid-cols-3 gap-2">
                {timeSlots.map(slot => (
                  <button
                    key={slot}
                    onClick={() => setSelectedTime(slot)}
                    className={`rounded-xl py-2.5 text-[10px] font-bold uppercase tracking-widest transition-all border ${
                      selectedTime === slot
                        ? 'bg-blue-600 border-blue-600 text-white ring-4 ring-blue-100 shadow-md'
                        : 'bg-white/40 border-white/40 text-slate-500 hover:border-blue-400 hover:text-blue-600'
                    }`}
                  >
                    {slot}
                  </button>
                ))}
              </div>
            </Card>

            <Card title="New Booking Detail">
               <form className="space-y-4" onSubmit={handleBooking}>
                 <Input 
                   label="Customer Name" 
                   placeholder="John Doe" 
                   value={customerName}
                   onChange={(e) => setCustomerName(e.target.value)}
                   disabled={isLoading}
                 />
                 <Input 
                   label="Phone Number" 
                   placeholder="+1 234 567 8900" 
                   value={phoneNumber}
                   onChange={(e) => setPhoneNumber(e.target.value)}
                   disabled={isLoading}
                 />
                 {message && (
                   <p className={cn(
                     "text-sm font-medium text-center",
                     message.type === 'success' ? "text-emerald-600" : "text-red-500"
                   )}>
                     {message.text}
                   </p>
                 )}
                 <Button 
                   type="submit" 
                   className="w-full text-xs font-bold uppercase tracking-widest py-3" 
                   isLoading={isLoading}
                   disabled={!selectedTime || !customerName || !phoneNumber}
                 >
                   Confirm Booking
                 </Button>
               </form>
            </Card>
          </div>
        </div>
      ) : (
        <Card>
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input placeholder="Search records..." className="pl-10" />
            </div>
            <Button variant="outline" className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
               <Download size={16} />
               Export CSV
            </Button>
          </div>
          <Table headers={['Name', 'Phone', 'Date', 'Time', 'Status']}>
            {bookingRecords.map((record, i) => (
              <TableRow key={i}>
                <TableCell className="font-bold text-slate-800">{record.name}</TableCell>
                <TableCell>{record.phone}</TableCell>
                <TableCell>{record.date}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <Clock size={12} className="text-slate-400" />
                    {record.time}
                  </div>
                </TableCell>
                <TableCell>
                  <div className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    record.status === 'Confirmed' ? 'bg-emerald-100 text-emerald-700' :
                    record.status === 'Completed' ? 'bg-blue-100 text-blue-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {record.status === 'Confirmed' && <CheckCircle2 size={12} />}
                    {record.status === 'Cancelled' && <XCircle size={12} />}
                    {record.status}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </Table>
        </Card>
      )}
    </div>
  );
};
