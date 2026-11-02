import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  SearchCode,
  History,
  Settings,
  BookOpen,
  ShieldAlert,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/new-analysis', label: 'New Analysis', icon: PlusCircle },
    { to: '/findings', label: 'Findings Explorer', icon: SearchCode },
    { to: '/history', label: 'Project History', icon: History },
    { to: '/settings', label: 'Settings', icon: Settings },
    { to: '/docs', label: 'Documentation', icon: BookOpen },
  ];

  return (
    <aside className="w-64 bg-[#0c1322] border-r border-[#1e2c4a] flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-[#1e2c4a]">
        <div className="p-2 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-lg shadow-md shadow-blue-500/20">
          <ShieldAlert className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
            CodeSentinel <span className="text-blue-400">AI</span>
          </h1>
          <p className="text-[10px] text-slate-400 font-medium">Quality & Security Engine</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#141f36]'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Mode / Status Footer */}
      <div className="p-4 border-t border-[#1e2c4a] bg-[#090e1a]/80">
        <div className="p-3 bg-[#111a2e] border border-[#1e2c4a] rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-semibold text-slate-300">Analysis Engines Ready</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            AST • Ruff • Bandit • Graph • Demo LLM
          </p>
        </div>
        <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>v1.0.0 Production</span>
          <span className="text-blue-400/80 font-mono">FastAPI + Vite</span>
        </div>
      </div>
    </aside>
  );
};
