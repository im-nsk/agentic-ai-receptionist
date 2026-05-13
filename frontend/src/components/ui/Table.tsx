import React from 'react';
import { cn } from '@/utils/cn';

interface TableProps {
  headers: string[];
  children: React.ReactNode;
  className?: string;
}

export const Table: React.FC<TableProps> = ({ headers, children, className }) => {
  return (
    <div
      className={cn(
        'relative w-full overflow-x-auto overflow-y-visible rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/80',
        className
      )}
    >
      <table className="w-full min-w-[36rem] caption-bottom text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-900">
            {headers.map((header) => (
              <th
                key={header}
                className="h-11 px-4 align-middle text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {children}
        </tbody>
      </table>
    </div>
  );
};

export const TableRow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <tr className={cn('transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/50', className)}>
    {children}
  </tr>
);

export const TableCell: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <td className={cn('px-4 py-3 align-middle text-slate-600 dark:text-slate-300', className)}>
    {children}
  </td>
);
