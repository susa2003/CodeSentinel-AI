import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettings, LLMTestResponse } from '../types';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [provider, setProvider] = useState('demo');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [apiBase, setApiBase] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [temperature, setTemperature] = useState(0.1);
  const [excludedDirs, setExcludedDirs] = useState('');

  // Engine toggles
  const [enableRuff, setEnableRuff] = useState(true);
  const [enableBandit, setEnableBandit] = useState(true);

  // Test LLM State
  const [testResult, setTestResult] = useState<LLMTestResponse | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await api.getSystemSettings();
      setSettings(data);
      setProvider(data.active_llm_provider || 'demo');
      setApiBase(data.settings.llm_api_base || '');
      setModel(data.settings.llm_model || 'gpt-4o-mini');
      setTemperature(data.settings.llm_temperature || 0.1);
      setEnableRuff(data.settings.ruff_enabled ?? true);
      setEnableBandit(data.settings.bandit_enabled ?? true);
      setExcludedDirs((data.settings.default_excluded_dirs || []).join(', '));
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError(null);
      const dirsList = excludedDirs.split(',').map((d) => d.trim()).filter(Boolean);
      await api.updateSystemSettings({
        llm_provider: provider,
        llm_api_key: apiKey ? apiKey : undefined,
        llm_api_base: apiBase ? apiBase : undefined,
        llm_model: model,
        llm_temperature: temperature,
        enable_ruff: enableRuff,
        enable_bandit: enableBandit,
        excluded_dirs: dirsList,
      });

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      fetchSettings();
    } catch (err: any) {
      setError(err?.message || 'Failed to update settings');
    }
  };

  const handleTestLLM = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const res = await api.testLLM({
        provider,
        api_key: apiKey || undefined,
        api_base: apiBase || undefined,
        model,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        provider,
        message: err?.response?.data?.message || err?.message || 'Test connection failed',
        is_demo_mode: false,
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400">
        <p className="text-sm">Loading system configurations...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Platform Settings</h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure analysis engines, exclusion boundaries, and optional LLM review credentials.
        </p>
      </div>

      {saveSuccess && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-800/60 rounded-xl text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Configuration saved successfully.</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* LLM Engine Configuration */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h3 className="text-base font-semibold text-white">AI Review Provider</h3>
            </div>
            {settings?.llm_has_api_key && (
              <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                API Key Configured
              </span>
            )}
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Deterministic Demo Mode runs fully offline using local heuristic evaluation. You may also configure an
            OpenAI-compatible, Gemini, or custom completions endpoint.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Review Provider Mode
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3.5 py-2 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="demo">Deterministic Demo Mode (Guaranteed offline / Heuristic)</option>
                <option value="openai">OpenAI (or OpenAI Compatible / v1/chat/completions)</option>
                <option value="gemini">Google Gemini (via OpenAI compat endpoint or proxy)</option>
                <option value="custom">Custom Host / Local LLM (Ollama, vLLM, LMStudio)</option>
              </select>
            </div>

            {provider !== 'demo' && (
              <>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      placeholder={settings?.llm_has_api_key ? '••••••••••••••••••••••••' : 'Enter API Key...'}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full pl-3.5 pr-10 py-2 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-2 text-slate-400 hover:text-white"
                    >
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                      Base URL (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="https://api.openai.com/v1"
                      value={apiBase}
                      onChange={(e) => setApiBase(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                      Model Identifier
                    </label>
                    <input
                      type="text"
                      placeholder="gpt-4o-mini"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Test Connection Button & Result */}
            <div className="pt-2 flex items-center gap-3">
              <button
                type="button"
                onClick={handleTestLLM}
                disabled={testing}
                className="px-3.5 py-2 bg-[#162238] hover:bg-[#1e2f50] border border-[#233557] rounded-lg text-xs font-semibold text-blue-400 transition-colors inline-flex items-center gap-2 cursor-pointer"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>{testing ? 'Testing connection...' : 'Test Connection'}</span>
              </button>

              {testResult && (
                <span
                  className={`text-xs px-2.5 py-1 rounded border ${
                    testResult.success
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-red-500/10 text-red-400 border-red-500/30'
                  }`}
                >
                  {testResult.message} {testResult.latency_ms ? `(${testResult.latency_ms}ms)` : ''}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Static Analyzers Configuration */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">Analysis Tool Integrations</h3>
          <p className="text-xs text-slate-400">
            System status of local binaries and analyzer adapters.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="p-3 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">Python AST Analyzer</span>
                <span className="text-[11px] text-slate-400">Standard library AST parser</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ACTIVE
              </span>
            </div>

            <div className="p-3 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">Polyglot Pattern Engine</span>
                <span className="text-[11px] text-slate-400">JS, TS, Java, HTML security checks</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ACTIVE
              </span>
            </div>

            <div className="p-3 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">Ruff Subprocess Adapter</span>
                <span className="text-[11px] text-slate-400">High-speed Python linter</span>
              </div>
              <input
                type="checkbox"
                checked={enableRuff}
                onChange={(e) => setEnableRuff(e.target.checked)}
                className="rounded text-blue-600 focus:ring-0"
              />
            </div>

            <div className="p-3 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">Bandit Security Adapter</span>
                <span className="text-[11px] text-slate-400">Python CWE vulnerability scanner</span>
              </div>
              <input
                type="checkbox"
                checked={enableBandit}
                onChange={(e) => setEnableBandit(e.target.checked)}
                className="rounded text-blue-600 focus:ring-0"
              />
            </div>
          </div>
        </div>

        {/* Exclusion Rules */}
        <div className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">Default Exclusion Directories</h3>
          <p className="text-xs text-slate-400">
            Comma-separated directory names that are excluded from manifest creation and static scans.
          </p>
          <textarea
            rows={3}
            value={excludedDirs}
            onChange={(e) => setExcludedDirs(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-xs text-white font-mono focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Save CTA */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
};
