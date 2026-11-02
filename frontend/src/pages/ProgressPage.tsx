import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { api } from '../services/api';
import { AnalysisProgress } from '../types';

export const ProgressPage: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();

  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  useEffect(() => {
    if (!analysisId) return;

    let timer: any = null;

    const poll = async () => {
      try {
        const data = await api.getAnalysisProgress(analysisId);
        setProgress(data);

        if (data.status === 'COMPLETED') {
          // brief pause to show 100%
          setTimeout(() => {
            navigate(`/analyses/${analysisId}`);
          }, 1200);
        } else if (data.status === 'RUNNING' || data.status === 'QUEUED') {
          timer = setTimeout(poll, 1500);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to fetch analysis progress');
      }
    };

    poll();

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [analysisId, navigate]);

  const handleCancel = async () => {
    if (!analysisId) return;
    try {
      setIsCancelling(true);
      await api.deleteOrCancelAnalysis(analysisId);
      setProgress((prev: AnalysisProgress | null) => (prev ? { ...prev, status: 'CANCELLED', current_stage: 'Cancelled by user' } : null));
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel analysis');
    } finally {
      setIsCancelling(false);
    }
  };

  if (!progress && !error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Connecting to CodeSentinel worker...</p>
        </div>
      </div>
    );
  }

  const stages = [
    { title: 'Archive Ingestion', desc: 'Secure decompression & ZipSlip validation', minPct: 5 },
    { title: 'Manifest Scan', desc: 'File detection, language identification, LOC', minPct: 20 },
    { title: 'Static Analyzers', desc: 'Python AST, Polyglot patterns, Ruff, Bandit', minPct: 35 },
    { title: 'Cross-File Graph', desc: 'Dependency mapping & symbol verification', minPct: 60 },
    { title: 'AI Code Review', desc: 'Context selection & structured review', minPct: 80 },
    { title: 'Persisting Findings', desc: 'Deduplication, normalization, report readiness', minPct: 95 },
  ];

  const currentPercent = progress?.progress_percent || 0;

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Analysis in Progress</h2>
        <p className="text-sm text-slate-400 mt-1">
          Analysis ID: <code className="text-blue-400 font-mono text-xs">{analysisId}</code>
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {/* Main Status & Progress Bar */}
      <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs uppercase font-semibold text-slate-400 tracking-wider">Current Stage</span>
            <h3 className="text-lg font-bold text-white mt-0.5">
              {progress?.current_stage || 'Processing...'}
            </h3>
            {progress?.stage_message && (
              <p className="text-xs text-slate-400 mt-1">{progress.stage_message}</p>
            )}
          </div>
          <div className="text-right">
            <span className="text-3xl font-extrabold text-blue-400 font-mono">{currentPercent}%</span>
            <div className="text-xs text-slate-500 mt-0.5">
              {progress?.status === 'COMPLETED' ? 'Completed' : progress?.status === 'CANCELLED' ? 'Cancelled' : 'Executing'}
            </div>
          </div>
        </div>

        {/* Progress Track */}
        <div className="w-full bg-[#0a0f1d] h-3 rounded-full overflow-hidden border border-[#1e2c4a]">
          <div
            className={`h-full transition-all duration-500 rounded-full ${
              progress?.status === 'FAILED'
                ? 'bg-red-500'
                : progress?.status === 'CANCELLED'
                ? 'bg-amber-500'
                : 'bg-gradient-to-r from-blue-600 to-indigo-500'
            }`}
            style={{ width: `${currentPercent}%` }}
          />
        </div>

        {/* Stage Timeline */}
        <div className="space-y-3 pt-2">
          {stages.map((st, idx) => {
            const isCompleted = currentPercent > st.minPct;
            const isCurrent = currentPercent >= st.minPct && (idx === stages.length - 1 || currentPercent < stages[idx + 1].minPct);
            return (
              <div key={st.title} className="flex items-center gap-3 text-sm">
                <div className="w-5 h-5 flex items-center justify-center shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : isCurrent ? (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                  ) : (
                    <div className="w-2.5 h-2.5 rounded-full bg-[#1e2c4a]" />
                  )}
                </div>
                <div className="flex-1">
                  <span className={`font-medium ${isCurrent ? 'text-white' : isCompleted ? 'text-slate-300' : 'text-slate-500'}`}>
                    {st.title}
                  </span>
                  <span className="text-xs text-slate-500 ml-2 hidden sm:inline">{st.desc}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Control Actions */}
      <div className="flex items-center justify-between">
        {progress?.status === 'RUNNING' || progress?.status === 'QUEUED' ? (
          <button
            type="button"
            onClick={handleCancel}
            disabled={isCancelling}
            className="px-4 py-2 bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-800/60 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            {isCancelling ? 'Cancelling Analysis...' : 'Cancel Analysis'}
          </button>
        ) : progress?.status === 'COMPLETED' ? (
          <Link
            to={`/analyses/${analysisId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition-colors"
          >
            <span>View Full Analysis Results</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        ) : (
          <Link
            to="/new-analysis"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
          >
            Start Another Analysis
          </Link>
        )}
      </div>
    </div>
  );
};
