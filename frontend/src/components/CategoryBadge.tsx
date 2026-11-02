import React from 'react';
import { Category } from '../types';

interface Props {
  category: Category;
}

export const CategoryBadge: React.FC<Props> = ({ category }) => {
  const configs: Record<Category, { text: string; bg: string }> = {
    SECURITY: { text: 'text-red-300', bg: 'bg-red-950/40 border-red-800/40' },
    BUG_RISK: { text: 'text-orange-300', bg: 'bg-orange-950/40 border-orange-800/40' },
    QUALITY: { text: 'text-blue-300', bg: 'bg-blue-950/40 border-blue-800/40' },
    PERFORMANCE: { text: 'text-yellow-300', bg: 'bg-yellow-950/40 border-yellow-800/40' },
    MAINTAINABILITY: { text: 'text-purple-300', bg: 'bg-purple-950/40 border-purple-800/40' },
    SYNTAX: { text: 'text-pink-300', bg: 'bg-pink-950/40 border-pink-800/40' },
    CROSS_FILE: { text: 'text-cyan-300', bg: 'bg-cyan-950/40 border-cyan-800/40' },
    TESTING: { text: 'text-emerald-300', bg: 'bg-emerald-950/40 border-emerald-800/40' },
  };

  const c = configs[category] || { text: 'text-slate-300', bg: 'bg-slate-900 border-slate-700' };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${c.bg} ${c.text}`}>
      {category.replace('_', ' ')}
    </span>
  );
};
