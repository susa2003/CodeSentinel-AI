import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionText?: string;
  actionLink?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<Props> = ({
  title,
  description,
  icon: Icon = Inbox,
  actionText,
  actionLink,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-[#111a2e]/60 border border-[#1e2c4a] rounded-xl border-dashed">
      <div className="p-3 bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20 mb-4">
        <Icon className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-slate-400 max-w-sm mb-6">{description}</p>
      {actionText && actionLink && (
        <Link
          to={actionLink}
          className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          {actionText}
        </Link>
      )}
      {actionText && onAction && !actionLink && (
        <button
          type="button"
          onClick={onAction}
          className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
