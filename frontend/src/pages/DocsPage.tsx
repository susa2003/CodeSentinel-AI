import React from 'react';
import {
  BookOpen,
  Cpu,
  Layers,
  Lock,
  FileCheck,
} from 'lucide-react';

export const DocsPage: React.FC = () => {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-10">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <BookOpen className="w-6 h-6 text-blue-400" />
          <span>CodeSentinel AI Documentation & Architecture</span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Production-style AI code review, static bug detection, and software quality analysis platform.
        </p>
      </div>

      {/* Section 1: Overview */}
      <section className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-blue-400" />
          <span>1. Core Platform Architecture</span>
        </h3>
        <p className="text-sm text-slate-300 leading-relaxed">
          CodeSentinel AI is designed around a multi-tier analysis pipeline that unites high-confidence deterministic
          static analyzers with contextual cross-file dependency mapping and optional LLM review.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="p-4 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider block mb-1">
              Tier 1: Deterministic
            </span>
            <p className="text-xs text-slate-400 leading-relaxed">
              Python AST parser, Ruff, Bandit, and Polyglot pattern rules identify syntax errors, security flaws, and
              anti-patterns with zero hallucinations.
            </p>
          </div>

          <div className="p-4 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg">
            <span className="text-xs font-bold text-purple-400 uppercase tracking-wider block mb-1">
              Tier 2: Cross-File Graph
            </span>
            <p className="text-xs text-slate-400 leading-relaxed">
              Analyzes import chains, builds symbol tables, detects circular dependencies, and identifies missing
              exported functions across modules.
            </p>
          </div>

          <div className="p-4 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block mb-1">
              Tier 3: AI Code Review
            </span>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inspects targeted high-risk context for logic flaws, boundary errors, and race conditions, validating
              all source lines against disk.
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Supported Analyzers */}
      <section className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <span>2. Supported Analyzers and Capabilities</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0c1322] text-slate-400 border-b border-[#1e2c4a]">
              <tr>
                <th className="p-3">Analyzer</th>
                <th className="p-3">Languages</th>
                <th className="p-3">Detection Scope</th>
                <th className="p-3">Execution Method</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2c4a] text-slate-300">
              <tr>
                <td className="p-3 font-semibold text-white">Python AST Engine</td>
                <td className="p-3">Python</td>
                <td className="p-3">Syntax errors, mutable defaults, eval/exec, insecure temp files, SQLi</td>
                <td className="p-3 font-mono text-emerald-400">Native Python AST</td>
              </tr>
              <tr>
                <td className="p-3 font-semibold text-white">Polyglot Pattern Engine</td>
                <td className="p-3">JS, TS, Java, HTML</td>
                <td className="p-3">DOM XSS, prototype pollution, template SQL injection, disabled TLS</td>
                <td className="p-3 font-mono text-emerald-400">Regex & Pattern Rules</td>
              </tr>
              <tr>
                <td className="p-3 font-semibold text-white">Ruff Adapter</td>
                <td className="p-3">Python</td>
                <td className="p-3">Flake8, Bugbear, Pyflakes, complexity, code style</td>
                <td className="p-3 font-mono text-blue-400">Isolated Subprocess</td>
              </tr>
              <tr>
                <td className="p-3 font-semibold text-white">Bandit Adapter</td>
                <td className="p-3">Python</td>
                <td className="p-3">CWE security vulnerabilities, shell=True, weak cryptographic hashes</td>
                <td className="p-3 font-mono text-blue-400">Isolated Subprocess</td>
              </tr>
              <tr>
                <td className="p-3 font-semibold text-white">Cross-File Engine</td>
                <td className="p-3">Polyglot</td>
                <td className="p-3">Circular dependencies, missing imported symbols, untested modules</td>
                <td className="p-3 font-mono text-purple-400">Graph Traversal</td>
              </tr>
              <tr>
                <td className="p-3 font-semibold text-white">AI Review / Demo</td>
                <td className="p-3">All Supported</td>
                <td className="p-3">Subtle logic bugs, boundary assumptions, missing error recovery</td>
                <td className="p-3 font-mono text-indigo-400">Structured JSON LLM</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 3: Safe Execution & Security Boundaries */}
      <section className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Lock className="w-5 h-5 text-emerald-400" />
          <span>3. Safe Execution Model & Security Boundaries</span>
        </h3>
        <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
          <div className="p-4 bg-[#0a0f1d] border-l-4 border-emerald-500 rounded-r-lg">
            <strong className="text-white block mb-1">Zero Arbitrary Execution Policy</strong>
            CodeSentinel AI strictly parses, inspects, and analyzes uploaded source code without executing setup scripts,
            running package managers (such as <code>npm install</code> or <code>pip install</code>), or launching project
            binaries on the host machine.
          </div>

          <div className="p-4 bg-[#0a0f1d] border-l-4 border-blue-500 rounded-r-lg">
            <strong className="text-white block mb-1">Archive Decompression Hardening (ZipSlip & Bomb Defense)</strong>
            Every entry in an uploaded ZIP archive is validated against path traversal (rejecting leading slashes,
            Windows drive letters, null bytes, and <code>..</code> segments). Decompression ratios are strictly verified
            to prevent Zip Bomb resource exhaustion attacks.
          </div>

          <div className="p-4 bg-[#0a0f1d] border-l-4 border-amber-500 rounded-r-lg">
            <strong className="text-white block mb-1">Automatic Secret Redaction</strong>
            Source code containing API keys, private certificates, or credentials is automatically redacted before
            generation of reports or inclusion in LLM context windows.
          </div>
        </div>
      </section>

      {/* Section 4: Human-in-the-Loop Verification Workflow */}
      <section className="bg-[#111a2e] border border-[#1e2c4a] rounded-xl p-6 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <FileCheck className="w-5 h-5 text-amber-400" />
          <span>4. Human Verification Workflow</span>
        </h3>
        <p className="text-sm text-slate-300 leading-relaxed">
          The platform distinguishes automated machine findings from AI hypotheses and verified statuses. Developers can
          audit each finding in the Findings Explorer and transition its verification state:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-1">
          <div className="p-3 bg-[#0a0f1d] border border-[#1e2c4a] rounded-lg text-center">
            <span className="text-xs font-semibold text-slate-400 block">Unreviewed</span>
            <span className="text-[11px] text-slate-500">Default triage state</span>
          </div>
          <div className="p-3 bg-[#0a0f1d] border border-red-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-red-400 block">Confirmed</span>
            <span className="text-[11px] text-slate-500">True positive bug</span>
          </div>
          <div className="p-3 bg-[#0a0f1d] border border-emerald-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-emerald-400 block">False Positive</span>
            <span className="text-[11px] text-slate-500">Intentional or invalid</span>
          </div>
          <div className="p-3 bg-[#0a0f1d] border border-blue-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-blue-400 block">Fixed</span>
            <span className="text-[11px] text-slate-500">Patched in codebase</span>
          </div>
          <div className="p-3 bg-[#0a0f1d] border border-amber-800/40 rounded-lg text-center">
            <span className="text-xs font-semibold text-amber-400 block">Accepted Risk</span>
            <span className="text-[11px] text-slate-500">Acknowledged trade-off</span>
          </div>
        </div>
      </section>
    </div>
  );
};
