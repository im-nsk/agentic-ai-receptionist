import React from 'react';
import { cn } from '../../lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  description?: string;
}

export const Card: React.FC<CardProps> = ({ children, className, title, description }) => {
  return (
    <div className={cn('glass-card p-6', className)}>
      {(title || description) && (
        <div className="mb-4 space-y-1.5">
          {title && <h3 className="text-lg font-bold leading-none tracking-tight text-slate-800">{title}</h3>}
          {description && <p className="text-sm font-medium text-slate-500">{description}</p>}
        </div>
      )}
      {children}
    </div>
  );
};
