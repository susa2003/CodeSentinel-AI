import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldAlert,
  AlertTriangle,
  FileCode2,
  ArrowRight,
  Layers,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { api } from '../services/api';
import { DashboardStats } from '../types';
import { StatCard } from '../components/StatCard';
import { EmptyState } from '../components/EmptyState';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading security metrics & analyses...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-8">
        <div className="p-4 bg-red-950/40 border border-red-800/50 rounded-xl text-red-300 text-sm">
          {error || 'Failed to load metrics'}
        </div>
      </div>
    );
  }

  if (stats.is_empty) {
    return (
      <div className="p-8 max-w-5xl mx-auto space-y-8">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Quality & Security Dashboard</h2>
          <p className="text-sm text-slate-400 mt-1">Real-time repository health, static tool findings, and AI review metrics</p>
        </div>
        <EmptyState
          title="No Project Analyses Yet"
          description="Upload a ZIP archive or submit individual source files to start deterministic static analysis, cross-file inspection, and AI review."
          actionText="Start First Analysis"
          actionLink="/new-analysis"
        />
      </div>
    );
  }

  // Prepare chart data
  const severityData = [
    { name: 'Critical', count: stats.findings_by_severity.CRITICAL || 0, color: '#ef4444' },
    { name: 'High', count: stats.findings_by_severity.HIGH || 0, color: '#f97316' },
    { name: 'Medium', count: stats.findings_by_severity.MEDIUM || 0, color: '#f59e0b' },
    { name: 'Low', count: stats.findings_by_severity.LOW || 0, color: '#3b82f6' },
    { name: 'Info', count: stats.findings_by_severity.INFORMATIONAL || 0, color: '#64748b' },
  ];

  const categoryData = Object.entries(stats.findings_by_category || {}).map(([cat, count]) => ({
    name: cat.replace('_', ' '),
    count: Number(count),
  }));

  const criticalHigh = (stats.findings_by_severity.CRITICAL || 0) + (stats.findings_by_severity.HIGH || 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Security & Quality Overview</h2>
          <p className="text-sm text-slate-400 mt-1">
            Aggregated diagnostics from Python AST, Ruff, Bandit, Pattern Engine, and AI Review
          </p>
        </div>
        <Link
          to="/new-analysis"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer self-start md:self-auto"
        >
          <span>New Analysis</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Analyses"
          value={stats.total_analyses}
          subtitle={`${stats.completed_analyses} completed successfully`}
          icon={Layers}
          color="blue"
        />
        <StatCard
          title="Total Findings"
          value={stats.total_findings}
          subtitle="Identified across all projects"
          icon={ShieldAlert}
          color="purple"
        />
        <StatCard
          title="Critical / High"
          value={criticalHigh}
          subtitle="Requires immediate attention"
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          title="Projects Tracked"
          value={stats.total_projects}
          subtitle="Active codebases registered"
          icon={FileCode2}
          color="emerald"
        />
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Breakdown Bar Chart */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-base font-semibold text-white">Findings by Severity</h3>
            <span className="text-xs text-slate-400 font-mono">Real-time DB Counts</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e2c4a', borderRadius: '8px' }}
                  labelStyle={{ color: '#fff', fontWeight: 600 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Categories Distribution */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-base font-semibold text-white">Findings by Category</h3>
            <span className="text-xs text-slate-400 font-mono">Categories Distribution</span>
          </div>
          <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
            {categoryData.length === 0 ? (
              <p className="text-sm text-slate-400">No categorised findings.</p>
            ) : (
              categoryData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <span className="text-slate-300 font-medium">{item.name}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-[#1e2c4a] h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-blue-500 h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (item.count / (stats.total_findings || 1)) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-mono font-semibold text-slate-400 w-8 text-right">
                      {item.count}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Analyses Table */}
      <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-[#1e2c4a] flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">Recent Analyses</h3>
          <Link to="/history" className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1">
            <span>View All History</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#0c1322] text-xs uppercase font-semibold text-slate-400 border-b border-[#1e2c4a]">
              <tr>
                <th className="px-6 py-3.5">Project</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Files / LOC</th>
                <th className="px-6 py-3.5">Findings</th>
                <th className="px-6 py-3.5">Duration</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2c4a]">
              {stats.recent_analyses.map((job) => (
                <tr key={job.id} className="hover:bg-[#141f36]/50 transition-colors">
                  <td className="px-6 py-4 font-medium text-white">{job.project_name}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                        job.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : job.status === 'RUNNING'
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                          : 'bg-red-500/10 text-red-400 border-red-500/30'
                      }`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-400">
                    {job.total_files} files • {job.total_lines} lines
                  </td>
                  <td className="px-6 py-4 font-mono font-medium text-amber-400">{job.total_findings}</td>
                  <td className="px-6 py-4 text-slate-400">{job.duration_seconds ? `${job.duration_seconds}s` : '-'}</td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      to={`/analyses/${job.id}`}
                      className="text-xs text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1"
                    >
                      <span>View Report</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
