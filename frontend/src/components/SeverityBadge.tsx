import React from 'react';
import { Severity } from '../types';

interface Props {
  severity: Severity;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<Props> = ({ severity, size = 'md' }) => {
  const configs: Record<Severity, { bg: string; text: string; border: string }> = {
    CRITICAL: {
      bg: 'bg-red-500/10',
      text: 'text-red-400',
      border: 'border-red-500/30',
    },
    HIGH: {
      bg: 'bg-orange-500/10',
      text: 'text-orange-400',
      border: 'border-orange-500/30',
    },
    MEDIUM: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
    },
    LOW: {
      bg: 'bg-blue-500/10',
      text: 'text-blue-400',
      border: 'border-blue-500/30',
    },
    INFORMATIONAL: {
      bg: 'bg-slate-500/10',
      text: 'text-slate-400',
      border: 'border-slate-500/30',
    },
  };

  const c = configs[severity] || configs.INFORMATIONAL;
  const sizeClasses = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center font-semibold rounded-md border ${c.bg} ${c.text} ${c.border} ${sizeClasses}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {severity}
    </span>
  );
};
