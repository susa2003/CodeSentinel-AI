import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileArchive,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';

export const NewAnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Analyzer options
  const [enableAst, setEnableAst] = useState(true);
  const [enablePatternEngine, setEnablePatternEngine] = useState(true);
  const [enableRuff, setEnableRuff] = useState(true);
  const [enableBandit, setEnableBandit] = useState(true);
  const [enableCrossFile, setEnableCrossFile] = useState(true);
  const [enableLlm, setEnableLlm] = useState(true);
  const [demoMode, setDemoMode] = useState(true);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      if (!projectName) {
        const defaultName = file.name.replace(/\.[^/.]+$/, '');
        setProjectName(defaultName);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!projectName) {
        const defaultName = file.name.replace(/\.[^/.]+$/, '');
        setProjectName(defaultName);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a ZIP archive or source file to analyze.');
      return;
    }
    if (!projectName.trim()) {
      setError('Please enter a project name.');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('project_name', projectName.trim());
      if (description.trim()) {
        formData.append('project_description', description.trim());
      }

      const options = {
        enable_ast: enableAst,
        enable_pattern_engine: enablePatternEngine,
        enable_ruff: enableRuff,
        enable_bandit: enableBandit,
        enable_cross_file: enableCrossFile,
        enable_llm_review: enableLlm,
        demo_mode: demoMode,
      };
      formData.append('options', JSON.stringify(options));

      if (selectedFile.name.endsWith('.zip')) {
        formData.append('archive_file', selectedFile);
      } else {
        formData.append('files', selectedFile);
      }

      const res = await api.createAnalysis(formData, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        }
      });

      navigate(`/analyses/${res.analysis_id}/progress`);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to initiate analysis';
      setError(msg);
      setUploading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Start New Code Analysis</h2>
        <p className="text-sm text-slate-400 mt-1">
          Upload a project archive (ZIP) or individual source file to trigger automated quality, security, and logic analysis.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Project Metadata */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">1. Project Details</h3>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Project Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g., auth-service or payment-gateway"
              className="w-full px-4 py-2.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Description (Optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief summary of this codebase or release tag"
              className="w-full px-4 py-2.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        </div>

        {/* File Ingestion Dropzone */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">2. Project Source File Ingestion</h3>
          <p className="text-xs text-slate-400">
            Securely uploaded with ZipSlip protection, bomb ratio limits, and automatic exclusion of build artifacts.
          </p>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
              isDragging
                ? 'border-blue-500 bg-blue-500/10'
                : selectedFile
                ? 'border-emerald-500/40 bg-emerald-500/5'
                : 'border-[#1e2c4a] hover:border-[#2b3e66] bg-[#0a0f1d]/60'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.py,.js,.ts,.tsx,.jsx,.java,.html"
              onChange={handleFileSelect}
              className="hidden"
            />

            {selectedFile ? (
              <div className="flex items-center gap-3 text-emerald-400">
                <FileArchive className="w-8 h-8" />
                <div className="text-left">
                  <p className="font-semibold text-sm text-white">{selectedFile.name}</p>
                  <p className="text-xs text-slate-400">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for analysis
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center">
                <div className="p-3 bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20 inline-flex mb-3">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <p className="text-sm font-semibold text-white">Click or drag & drop ZIP project archive here</p>
                <p className="text-xs text-slate-400 mt-1">Supports .zip archives or individual source files (.py, .ts, .js)</p>
              </div>
            )}
          </div>
        </div>

        {/* Analyzer Selection Toggles */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">3. Configure Analysis Engines</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* AST */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enableAst}
                onChange={(e) => setEnableAst(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">Python AST Static Engine</span>
                <span className="text-xs text-slate-400">Syntax errors, mutable defaults, dangerous eval, SQLi</span>
              </div>
            </label>

            {/* Pattern */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enablePatternEngine}
                onChange={(e) => setEnablePatternEngine(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">Polyglot Pattern Engine</span>
                <span className="text-xs text-slate-400">JS/TS innerHTML XSS, Prototype Pollution, Insecure TLS</span>
              </div>
            </label>

            {/* Ruff */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enableRuff}
                onChange={(e) => setEnableRuff(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">Ruff Linter & Analyzer</span>
                <span className="text-xs text-slate-400">High-speed AST rules, bugbear, unused imports, flake8</span>
              </div>
            </label>

            {/* Bandit */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enableBandit}
                onChange={(e) => setEnableBandit(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">Bandit Security Scanner</span>
                <span className="text-xs text-slate-400">CWE security vulnerabilities, shell execution, crypto</span>
              </div>
            </label>

            {/* Cross File */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enableCrossFile}
                onChange={(e) => setEnableCrossFile(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">Cross-File Dependency Graph</span>
                <span className="text-xs text-slate-400">Circular dependencies, missing exported symbols, test coverage</span>
              </div>
            </label>

            {/* AI Review */}
            <label className="flex items-start gap-3 p-3.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg cursor-pointer hover:border-[#2b3e66] transition-colors">
              <input
                type="checkbox"
                checked={enableLlm}
                onChange={(e) => setEnableLlm(e.target.checked)}
                className="mt-1 rounded text-blue-600 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-white block">AI Code Review Service</span>
                <span className="text-xs text-slate-400">Targeted logic flaw detection & regression test proposal</span>
              </div>
            </label>
          </div>

          {enableLlm && (
            <div className="mt-4 p-4 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <div>
                  <span className="text-xs font-semibold text-slate-200">Deterministic Demo Review Mode</span>
                  <p className="text-[11px] text-slate-400">
                    Runs offline with reproducible heuristics. Disable to use configured external LLM API key.
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="rounded text-blue-600 focus:ring-0"
              />
            </div>
          )}
        </div>

        {/* Submit Button & Progress */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Safe execution model: Source code is never executed directly on the host machine.
          </p>
          <button
            type="submit"
            disabled={uploading || !selectedFile}
            className={`px-6 py-3 rounded-lg text-sm font-semibold transition-all shadow-md cursor-pointer ${
              uploading || !selectedFile
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20'
            }`}
          >
            {uploading ? `Uploading & Initializing (${uploadProgress}%)` : 'Start CodeSentinel Analysis'}
          </button>
        </div>
      </form>
    </div>
  );
};
