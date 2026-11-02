import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Trash2,
  ExternalLink,
  Download,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { api } from '../services/api';
import { AnalysisJob } from '../types';
import { EmptyState } from '../components/EmptyState';

export const HistoryPage: React.FC = () => {
  const [analyses, setAnalyses] = useState<AnalysisJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    fetchAnalyses();
  }, []);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      const res = await api.listAnalyses({ page_size: 100 });
      setAnalyses(res.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string, projectName: string) => {
    if (!window.confirm(`Are you sure you want to delete analysis for '${projectName}'?`)) {
      return;
    }
    try {
      await api.deleteOrCancelAnalysis(id);
      setAnalyses((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      alert(`Failed to delete analysis: ${err?.message || 'Unknown error'}`);
    }
  };

  const filtered = analyses.filter((a) => {
    if (statusFilter !== 'ALL' && a.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        (a.project_name || '').toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Project Analysis History</h2>
          <p className="text-sm text-slate-400 mt-1">
            Historical audit log of all completed, running, and archived security & quality scans.
          </p>
        </div>
        <Link
          to="/new-analysis"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm self-start sm:self-auto"
        >
          <span>Run New Scan</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {/* Filter Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by project name or analysis ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-[#0a0f1d] border border-[#1e2c4a] text-xs text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
        >
          <option value="ALL">All Statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="RUNNING">Running</option>
          <option value="FAILED">Failed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      {/* Analyses Table or Empty State */}
      {loading ? (
        <div className="flex items-center justify-center p-16 text-slate-400 text-sm">
          Loading history records...
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No Matching Analyses Found"
          description={
            analyses.length === 0
              ? 'No project scans have been conducted yet.'
              : 'No analyses matched the selected search criteria.'
          }
          actionText={analyses.length === 0 ? 'Start Analysis' : undefined}
          actionLink={analyses.length === 0 ? '/new-analysis' : undefined}
        />
      ) : (
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#0c1322] text-xs uppercase font-semibold text-slate-400 border-b border-[#1e2c4a]">
                <tr>
                  <th className="px-6 py-3.5">Project</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Date & Time</th>
                  <th className="px-6 py-3.5">Files / LOC</th>
                  <th className="px-6 py-3.5">Findings</th>
                  <th className="px-6 py-3.5">Duration</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2c4a]">
                {filtered.map((item) => (
                  <tr key={item.id} className="hover:bg-[#141f36]/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-white">{item.project_name || 'Untitled Project'}</div>
                      <div className="text-[11px] font-mono text-slate-500 mt-0.5">{item.id}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                          item.status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : item.status === 'RUNNING'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                            : 'bg-red-500/10 text-red-400 border-red-500/30'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-300">
                      {item.total_files} files • {item.total_lines} lines
                    </td>
                    <td className="px-6 py-4 font-mono font-semibold text-amber-400">
                      {item.total_findings}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {item.duration_seconds ? `${item.duration_seconds}s` : '-'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/analyses/${item.id}`}
                          className="p-1.5 hover:bg-[#1e2c4a] rounded text-blue-400 hover:text-blue-300 transition-colors"
                          title="View Analysis Details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                        <a
                          href={api.getReportDownloadUrl(item.id, 'html')}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 hover:bg-[#1e2c4a] rounded text-slate-400 hover:text-white transition-colors"
                          title="Download HTML Report"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          type="button"
                          onClick={() => handleDelete(item.id, item.project_name || 'Project')}
                          className="p-1.5 hover:bg-red-950/50 rounded text-red-400 hover:text-red-300 transition-colors cursor-pointer"
                          title="Delete Analysis"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
