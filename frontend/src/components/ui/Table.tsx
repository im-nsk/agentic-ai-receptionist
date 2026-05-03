import React from 'react';
import { cn } from '../../lib/utils';

interface TableProps {
  headers: string[];
  children: React.ReactNode;
  className?: string;
}

export const Table: React.FC<TableProps> = ({ headers, children, className }) => {
  return (
    <div className={cn('relative w-full overflow-auto rounded-2xl border border-white/20 bg-white/10 shadow-sm', className)}>
      <table className="w-full caption-bottom text-sm text-left">
        <thead className="bg-white/20">
          <tr className="border-b border-white/10 transition-colors">
            {headers.map((header) => (
              <th key={header} className="h-12 px-6 align-middle font-bold text-xs uppercase tracking-widest text-slate-400">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_tr:last-child]:border-0 divide-y divide-white/10">
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
  <tr className={cn('transition-colors hover:bg-white/20', className)}>
    {children}
  </tr>
);

export const TableCell: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <td className={cn('px-6 py-4 align-middle text-slate-600 font-medium', className)}>
    {children}
  </td>
);
