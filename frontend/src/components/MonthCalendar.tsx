import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/utils/cn';
import { toISODateLocal } from '@/utils/bookingStorage';
import { Button } from '@/components/ui/Button';

interface MonthCalendarProps {
  selected: Date;
  onSelect: (d: Date) => void;
}

const weekday = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

export const MonthCalendar: React.FC<MonthCalendarProps> = ({ selected, onSelect }) => {
  const [visible, setVisible] = useState(() => startOfMonth(selected));

  const { label, cells } = useMemo(() => {
    const first = startOfMonth(visible);
    const last = new Date(visible.getFullYear(), visible.getMonth() + 1, 0);
    const pad = first.getDay();
    const daysInMonth = last.getDate();

    const cellsArr: { date: Date; inMonth: boolean }[] = [];
    const prevLast = new Date(visible.getFullYear(), visible.getMonth(), 0).getDate();

    for (let i = pad - 1; i >= 0; i -= 1) {
      cellsArr.push({
        date: new Date(visible.getFullYear(), visible.getMonth() - 1, prevLast - i),
        inMonth: false,
      });
    }

    for (let d = 1; d <= daysInMonth; d += 1) {
      cellsArr.push({
        date: new Date(visible.getFullYear(), visible.getMonth(), d),
        inMonth: true,
      });
    }

    let tail = 1;
    while (cellsArr.length % 7 !== 0) {
      cellsArr.push({
        date: new Date(visible.getFullYear(), visible.getMonth() + 1, tail),
        inMonth: false,
      });
      tail += 1;
    }

    return {
      label: visible.toLocaleString(undefined, { month: 'long', year: 'numeric' }),
      cells: cellsArr,
    };
  }, [visible]);

  const selectedIso = toISODateLocal(selected);
  const todayIso = toISODateLocal(new Date());

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          className="min-w-9 px-2"
          onClick={() => setVisible((v) => new Date(v.getFullYear(), v.getMonth() - 1, 1))}
          aria-label="Previous month"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-50">{label}</span>
        <Button
          variant="outline"
          size="sm"
          className="min-w-9 px-2"
          onClick={() => setVisible((v) => new Date(v.getFullYear(), v.getMonth() + 1, 1))}
          aria-label="Next month"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {weekday.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map(({ date, inMonth }) => {
          const iso = toISODateLocal(date);
          const isSelected = iso === selectedIso;
          const isToday = iso === todayIso;
          return (
            <button
              key={`${iso}-${inMonth}`}
              type="button"
              onClick={() => onSelect(date)}
              className={cn(
                'flex h-9 items-center justify-center rounded-lg text-sm font-medium transition-colors',
                !inMonth && 'text-slate-300 dark:text-slate-600',
                inMonth && 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800',
                isSelected && 'bg-blue-600 text-white shadow-md hover:bg-blue-600 dark:hover:bg-blue-600',
                !isSelected && isToday && inMonth && 'ring-1 ring-blue-500/50'
              )}
            >
              {date.getDate()}
            </button>
          );
        })}
      </div>
    </div>
  );
};
