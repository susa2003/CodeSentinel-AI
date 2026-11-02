import React, { useState } from 'react';
import { VerificationStatus } from '../types';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, HelpCircle, ChevronDown } from 'lucide-react';

interface Props {
  status: VerificationStatus;
  onChangeStatus?: (newStatus: VerificationStatus) => void;
  interactive?: boolean;
}

export const StatusBadge: React.FC<Props> = ({ status, onChangeStatus, interactive = false }) => {
  const [isOpen, setIsOpen] = useState(false);

  const configs: Record<VerificationStatus, { label: string; text: string; bg: string; icon: any }> = {
    UNREVIEWED: { label: 'Unreviewed', text: 'text-slate-400', bg: 'bg-slate-800/60 border-slate-700', icon: HelpCircle },
    CONFIRMED: { label: 'Confirmed Bug', text: 'text-red-400', bg: 'bg-red-950/50 border-red-800/60', icon: AlertTriangle },
    FALSE_POSITIVE: { label: 'False Positive', text: 'text-emerald-400', bg: 'bg-emerald-950/50 border-emerald-800/60', icon: CheckCircle2 },
    FIXED: { label: 'Fixed', text: 'text-blue-400', bg: 'bg-blue-950/50 border-blue-800/60', icon: ShieldCheck },
    ACCEPTED_RISK: { label: 'Accepted Risk', text: 'text-amber-400', bg: 'bg-amber-950/50 border-amber-800/60', icon: XCircle },
  };

  const current = configs[status] || configs.UNREVIEWED;
  const Icon = current.icon;

  const statuses: VerificationStatus[] = ['UNREVIEWED', 'CONFIRMED', 'FALSE_POSITIVE', 'FIXED', 'ACCEPTED_RISK'];

  if (!interactive) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${current.bg} ${current.text}`}>
        <Icon className="w-3.5 h-3.5" />
        {current.label}
      </span>
    );
  }

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${current.bg} ${current.text} hover:opacity-90`}
      >
        <Icon className="w-3.5 h-3.5" />
        <span>{current.label}</span>
        <ChevronDown className="w-3 h-3 ml-0.5 opacity-60" />
      </button>

      {isOpen && (
        <div className="absolute right-0 z-30 mt-1 w-44 rounded-md bg-[#162238] border border-[#233557] shadow-xl py-1 text-xs">
          {statuses.map((st) => {
            const itemConfig = configs[st];
            const ItemIcon = itemConfig.icon;
            const isSelected = st === status;
            return (
              <button
                key={st}
                type="button"
                onClick={() => {
                  onChangeStatus?.(st);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-[#1e2f50] transition-colors ${
                  isSelected ? 'bg-[#1e2f50]/80 font-semibold' : ''
                } ${itemConfig.text}`}
              >
                <ItemIcon className="w-3.5 h-3.5" />
                <span>{itemConfig.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
