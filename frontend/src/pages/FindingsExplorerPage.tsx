import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Search,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  ArrowLeft,
  RefreshCw,
  FileCode,
} from 'lucide-react';
import { api } from '../services/api';
import { Finding, VerificationStatus } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { StatusBadge } from '../components/StatusBadge';
import { CodeViewer } from '../components/CodeViewer';

export const FindingsExplorerPage: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();

  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [aiFilter, setAiFilter] = useState<'ALL' | 'AI_ONLY' | 'STATIC_ONLY'>('ALL');

  // File content cache for Monaco editor
  const [fileContent, setFileContent] = useState<string>('');
  const [fileLoading, setFileLoading] = useState(false);
  const [statusNotes, setStatusNotes] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchFindings();
  }, [analysisId, selectedSeverity, selectedCategory, selectedStatus, aiFilter]);

  const fetchFindings = async () => {
    if (!analysisId) return;
    try {
      setLoading(true);
      const params: Record<string, any> = { page_size: 150 };
      if (selectedSeverity !== 'ALL') params.severity = selectedSeverity;
      if (selectedCategory !== 'ALL') params.category = selectedCategory;
      if (selectedStatus !== 'ALL') params.verification_status = selectedStatus;
      if (aiFilter === 'AI_ONLY') params.is_ai = true;
      if (aiFilter === 'STATIC_ONLY') params.is_ai = false;
      if (search.trim()) params.search = search.trim();

      const res = await api.listFindings(analysisId, params);
      setFindings(res.items);
      if (res.items.length > 0 && !selectedFinding) {
        setSelectedFinding(res.items[0]);
      } else if (res.items.length > 0 && selectedFinding) {
        // Keep selected if still in list, else pick first
        const found = res.items.find((f) => f.id === selectedFinding.id);
        setSelectedFinding(found || res.items[0]);
      } else {
        setSelectedFinding(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch findings');
    } finally {
      setLoading(false);
    }
  };

  // When selected finding changes, fetch file content for Monaco Editor
  useEffect(() => {
    if (!selectedFinding || !analysisId) return;

    let isMounted = true;
    const fetchFile = async () => {
      try {
        setFileLoading(true);
        const res = await api.getFileContent(analysisId, selectedFinding.file_path);
        if (isMounted) {
          setFileContent(res.content);
        }
      } catch (err) {
        if (isMounted) {
          setFileContent(selectedFinding.evidence || '// Source file could not be retrieved from workspace.');
        }
      } finally {
        if (isMounted) setFileLoading(false);
      }
    };

    fetchFile();
    setStatusNotes('');

    return () => {
      isMounted = false;
    };
  }, [selectedFinding, analysisId]);

  const handleStatusChange = async (newStatus: VerificationStatus) => {
    if (!selectedFinding) return;
    try {
      const updated = await api.updateFindingStatus(selectedFinding.id, newStatus, statusNotes);
      setSelectedFinding(updated);
      setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
    } catch (err: any) {
      alert(`Failed to update status: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleCopyFinding = () => {
    if (!selectedFinding) return;
    const reportText = `[${selectedFinding.severity}] ${selectedFinding.title}\nRule: ${selectedFinding.rule_id} (${selectedFinding.source_analyzer})\nLocation: ${selectedFinding.file_path}:${selectedFinding.start_line}\nVerification: ${selectedFinding.verification_status}\n\nExplanation:\n${selectedFinding.explanation}\n\nRemediation:\n${selectedFinding.remediation || 'N/A'}`;
    navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredFindings = findings.filter((f) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      f.title.toLowerCase().includes(q) ||
      f.rule_id.toLowerCase().includes(q) ||
      f.file_path.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col h-[calc(100vh-1px)] overflow-hidden">
      {/* Subheader / Bar */}
      <div className="h-14 border-b border-[#1e2c4a] bg-[#0c1322] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to={analysisId ? `/analyses/${analysisId}` : '/'}
            className="p-1.5 hover:bg-[#162238] rounded-md text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <span>Findings Explorer</span>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono border border-blue-500/20">
              {filteredFindings.length} Issues
            </span>
          </h2>
        </div>

        {/* Global Filter Pills */}
        <div className="flex items-center gap-2">
          <select
            value={aiFilter}
            onChange={(e) => setAiFilter(e.target.value as any)}
            className="bg-[#111a2e] border border-[#1e2c4a] text-xs text-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Sources (Static & AI)</option>
            <option value="STATIC_ONLY">Deterministic Static Tools Only</option>
            <option value="AI_ONLY">AI / Heuristic Review Only</option>
          </select>

          <button
            onClick={fetchFindings}
            title="Refresh findings"
            className="p-1.5 hover:bg-[#162238] rounded text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Split-Pane Workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane: Finding List & Filters */}
        <div className="w-96 border-r border-[#1e2c4a] bg-[#0f172a] flex flex-col shrink-0">
          {/* Search & Select Filters */}
          <div className="p-3 border-b border-[#1e2c4a] space-y-2 bg-[#0c1322]/80">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search rule, title, or file..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-[#080d18] border border-[#1e2c4a] rounded text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="bg-[#080d18] border border-[#1e2c4a] text-xs text-slate-300 rounded px-2 py-1 focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
                <option value="INFORMATIONAL">Info</option>
              </select>

              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-[#080d18] border border-[#1e2c4a] text-xs text-slate-300 rounded px-2 py-1 focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="UNREVIEWED">Unreviewed</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="FALSE_POSITIVE">False Positive</option>
                <option value="FIXED">Fixed</option>
                <option value="ACCEPTED_RISK">Accepted Risk</option>
              </select>
            </div>
          </div>

          {/* Finding Cards List */}
          <div className="flex-1 overflow-y-auto divide-y divide-[#1e2c4a]">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading findings...</div>
            ) : filteredFindings.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">No findings match active filters.</div>
            ) : (
              filteredFindings.map((f) => {
                const isSelected = selectedFinding?.id === f.id;
                return (
                  <div
                    key={f.id}
                    onClick={() => setSelectedFinding(f)}
                    className={`p-3.5 cursor-pointer transition-colors ${
                      isSelected ? 'bg-blue-600/10 border-l-4 border-l-blue-500' : 'hover:bg-[#141f36]/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <SeverityBadge severity={f.severity} size="sm" />
                      <span className="text-[10px] font-mono text-slate-500">{f.source_analyzer}</span>
                    </div>
                    <h4 className="text-xs font-semibold text-white line-clamp-2 leading-snug">{f.title}</h4>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span className="truncate max-w-[190px]">{f.file_path}</span>
                      <span className="text-amber-400/90 font-semibold">L{f.start_line}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-1.5">
                      <StatusBadge status={f.verification_status} />
                      {f.is_ai_suggested && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">
                          <Sparkles className="w-2.5 h-2.5" />
                          {f.is_demo ? 'Demo AI' : 'AI'}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Pane: Code Viewer & Detailed Finding Inspection */}
        <div className="flex-1 flex flex-col overflow-y-auto bg-[#0a0f1d]">
          {selectedFinding ? (
            <div className="p-6 space-y-6">
              {/* Finding Header Card */}
              <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <SeverityBadge severity={selectedFinding.severity} />
                      <CategoryBadge category={selectedFinding.category} />
                      <span className="text-xs font-mono text-slate-400 bg-[#0c1322] px-2 py-0.5 rounded border border-[#1e2c4a]">
                        Rule: {selectedFinding.rule_id}
                      </span>
                      {selectedFinding.is_ai_suggested && (
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 font-medium border border-purple-500/30 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          {selectedFinding.is_demo ? 'Deterministic Demo Mode' : 'AI Review Hypothesis'}
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-bold text-white">{selectedFinding.title}</h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleCopyFinding}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-[#162238] hover:bg-[#1e2f50] border border-[#233557] rounded-lg text-xs font-medium text-slate-300 transition-colors cursor-pointer"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied' : 'Copy Finding'}</span>
                    </button>

                    {selectedFinding.doc_url && (
                      <a
                        href={selectedFinding.doc_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-[#162238] hover:bg-[#1e2f50] border border-[#233557] rounded-lg text-xs font-medium text-blue-400 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>Docs</span>
                      </a>
                    )}
                  </div>
                </div>

                {/* Verification Workflow Control */}
                <div className="p-4 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-semibold text-slate-300 block">Verification Status</span>
                    <span className="text-[11px] text-slate-500">
                      Distinguish AI hypothesis from human confirmed findings
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge
                      status={selectedFinding.verification_status}
                      interactive={true}
                      onChangeStatus={handleStatusChange}
                    />
                  </div>
                </div>

                {/* Description & Explanation */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Problem Explanation
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                    {selectedFinding.explanation}
                  </p>
                </div>

                {/* Suggested Remediation */}
                {selectedFinding.remediation && (
                  <div className="bg-blue-950/20 border-l-4 border-blue-500 rounded-r-lg p-4 space-y-1">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-blue-400">
                      Suggested Remediation & Fix
                    </h4>
                    <p className="text-sm text-blue-200/90 whitespace-pre-line leading-relaxed">
                      {selectedFinding.remediation}
                    </p>
                  </div>
                )}
              </div>

              {/* Monaco Code Viewer Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileCode className="w-4 h-4 text-blue-400" />
                    <span>Source Code Location & Context</span>
                  </h4>
                  <span className="text-xs font-mono text-slate-400">
                    {selectedFinding.file_path}:{selectedFinding.start_line}
                  </span>
                </div>

                {fileLoading ? (
                  <div className="h-64 flex items-center justify-center bg-[#0c1322] border border-[#1e2c4a] rounded-xl text-slate-400 text-sm">
                    Retrieving file from workspace...
                  </div>
                ) : (
                  <CodeViewer
                    code={fileContent}
                    fileName={selectedFinding.file_path}
                    highlightLine={selectedFinding.start_line}
                    language={selectedFinding.file_path.split('.').pop() || 'python'}
                    height="420px"
                  />
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
              Select a finding from the left pane to view details and inspect source code.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
