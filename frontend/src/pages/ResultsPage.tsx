import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Download,
  SearchCode,
} from 'lucide-react';
import { api } from '../services/api';
import { AnalysisDetail, AnalyzerRecord } from '../types';

export const ResultsPage: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    fetchDetail();
  }, [analysisId]);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const data = await api.getAnalysisDetail(analysisId!);
      setDetail(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch analysis details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading analysis report...</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8">
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm">
          {error || 'Failed to load report'}
        </div>
      </div>
    );
  }

  const criticalCount = detail.severity_counts.CRITICAL || 0;
  const highCount = detail.severity_counts.HIGH || 0;
  const mediumCount = detail.severity_counts.MEDIUM || 0;
  const lowCount = detail.severity_counts.LOW || 0;
  const infoCount = detail.severity_counts.INFORMATIONAL || 0;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Executive Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mb-1">
            <span>Project: <strong className="text-white">{detail.project_name}</strong></span>
            <span>•</span>
            <span>Analysis ID: <code>{detail.id}</code></span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Analysis Executive Summary
          </h2>
        </div>

        {/* Action Buttons: Explorer CTA & Report Downloads */}
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={`/analyses/${analysisId}/findings`}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
          >
            <SearchCode className="w-4 h-4" />
            <span>Open Findings Explorer</span>
          </Link>

          {/* Export Dropdown / Buttons */}
          <a
            href={api.getReportDownloadUrl(detail.id, 'html')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#111a2e] hover:bg-[#162238] border border-[#1e2c4a] rounded-lg text-xs font-medium text-slate-300 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>HTML</span>
          </a>

          <a
            href={api.getReportDownloadUrl(detail.id, 'json')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#111a2e] hover:bg-[#162238] border border-[#1e2c4a] rounded-lg text-xs font-medium text-slate-300 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>JSON</span>
          </a>

          <a
            href={api.getReportDownloadUrl(detail.id, 'markdown')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#111a2e] hover:bg-[#162238] border border-[#1e2c4a] rounded-lg text-xs font-medium text-slate-300 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-purple-400" />
            <span>Markdown</span>
          </a>
        </div>
      </div>

      {/* High-level Scorecard */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Findings</span>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">{detail.total_findings}</div>
          <div className="text-xs text-slate-500 mt-1">Across all static & AI engines</div>
        </div>

        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">High & Critical Risks</span>
          <div className="text-3xl font-extrabold text-red-400 mt-2 font-mono">{criticalCount + highCount}</div>
          <div className="text-xs text-slate-500 mt-1">{criticalCount} Critical • {highCount} High</div>
        </div>

        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Files Scanned</span>
          <div className="text-3xl font-extrabold text-blue-400 mt-2 font-mono">{detail.total_files}</div>
          <div className="text-xs text-slate-500 mt-1">{detail.total_lines.toLocaleString()} lines of code</div>
        </div>

        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Analysis Duration</span>
          <div className="text-3xl font-extrabold text-emerald-400 mt-2 font-mono">
            {detail.duration_seconds ? `${detail.duration_seconds}s` : '-'}
          </div>
          <div className="text-xs text-slate-500 mt-1">{detail.detected_languages.join(', ') || 'Polyglot'}</div>
        </div>
      </div>

      {/* Severity Breakdown Bar */}
      <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
        <h3 className="text-base font-semibold text-white">Severity Distribution</h3>
        <div className="grid grid-cols-5 gap-3">
          <div className="p-3 bg-red-950/20 border border-red-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-red-400 block">CRITICAL</span>
            <span className="text-2xl font-bold text-white font-mono">{criticalCount}</span>
          </div>
          <div className="p-3 bg-orange-950/20 border border-orange-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-orange-400 block">HIGH</span>
            <span className="text-2xl font-bold text-white font-mono">{highCount}</span>
          </div>
          <div className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-amber-400 block">MEDIUM</span>
            <span className="text-2xl font-bold text-white font-mono">{mediumCount}</span>
          </div>
          <div className="p-3 bg-blue-950/20 border border-blue-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-blue-400 block">LOW</span>
            <span className="text-2xl font-bold text-white font-mono">{lowCount}</span>
          </div>
          <div className="p-3 bg-slate-900/40 border border-slate-700/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-slate-400 block">INFO</span>
            <span className="text-2xl font-bold text-white font-mono">{infoCount}</span>
          </div>
        </div>
      </div>

      {/* Analyzer Execution Breakdown Table */}
      <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-[#1e2c4a]">
          <h3 className="text-base font-semibold text-white">Configured Analysis Engines Status</h3>
          <p className="text-xs text-slate-400 mt-1">
            Detailed record of which tools were executed, skipped, or produced findings.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#0c1322] text-xs uppercase font-semibold text-slate-400 border-b border-[#1e2c4a]">
              <tr>
                <th className="px-6 py-3.5">Analyzer</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Duration</th>
                <th className="px-6 py-3.5">Findings Count</th>
                <th className="px-6 py-3.5">Execution Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2c4a]">
              {detail.analyzer_records.map((r: AnalyzerRecord) => (
                <tr key={r.id} className="hover:bg-[#141f36]/40 transition-colors">
                  <td className="px-6 py-4 font-semibold text-white">{r.analyzer_name}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                        r.status === 'SUCCESS'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : r.status === 'SKIPPED'
                          ? 'bg-slate-500/10 text-slate-400 border-slate-500/30'
                          : 'bg-red-500/10 text-red-400 border-red-500/30'
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-400 font-mono">{r.duration_seconds}s</td>
                  <td className="px-6 py-4 font-mono font-medium text-white">{r.findings_count}</td>
                  <td className="px-6 py-4 text-slate-400 text-xs">{r.message || r.skip_reason || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
