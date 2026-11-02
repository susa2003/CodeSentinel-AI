import React from 'react';
import { LucideIcon } from 'lucide-react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'blue' | 'purple' | 'red' | 'amber' | 'emerald';
}

export const StatCard: React.FC<Props> = ({ title, value, subtitle, icon: Icon, color = 'blue' }) => {
  const colorMap = {
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    red: 'text-red-400 bg-red-500/10 border-red-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  };

  const badgeStyle = colorMap[color] || colorMap.blue;

  return (
    <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-5 hover:border-[#2b3e66] transition-colors shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`p-2 rounded-lg border ${badgeStyle}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-white">{value}</span>
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
};
