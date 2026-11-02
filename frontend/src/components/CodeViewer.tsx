import React, { useRef, useEffect, useState } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { Copy, Check, FileCode } from 'lucide-react';

interface Props {
  code: string;
  language?: string;
  highlightLine?: number;
  fileName?: string;
  height?: string;
}

export const CodeViewer: React.FC<Props> = ({
  code,
  language = 'python',
  highlightLine,
  fileName,
  height = '450px',
}) => {
  const editorRef = useRef<any>(null);
  const [copied, setCopied] = useState(false);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    if (highlightLine && highlightLine > 0) {
      editor.revealLineInCenter(highlightLine);
      editor.deltaDecorations(
        [],
        [
          {
            range: new monaco.Range(highlightLine, 1, highlightLine, 1),
            options: {
              isWholeLine: true,
              className: 'bg-red-500/20 border-l-4 border-red-500',
              glyphMarginClassName: 'bg-red-500',
            },
          },
        ]
      );
    }
  };

  useEffect(() => {
    if (editorRef.current && highlightLine && highlightLine > 0) {
      editorRef.current.revealLineInCenter(highlightLine);
    }
  }, [highlightLine]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getMonacoLang = (lang: string) => {
    const l = lang.toLowerCase();
    if (l.includes('py')) return 'python';
    if (l.includes('type') || l === 'ts' || l === 'tsx') return 'typescript';
    if (l.includes('script') || l === 'js' || l === 'jsx') return 'javascript';
    if (l.includes('java')) return 'java';
    if (l.includes('html')) return 'html';
    if (l.includes('css')) return 'css';
    if (l.includes('json')) return 'json';
    return 'plaintext';
  };

  return (
    <div className="flex flex-col rounded-xl overflow-hidden border border-[#1e2c4a] bg-[#0c1322]">
      {fileName && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#0f172a] border-b border-[#1e2c4a]">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
            <FileCode className="w-4 h-4 text-blue-400" />
            <span>{fileName}</span>
            {highlightLine && (
              <span className="text-amber-400 font-semibold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                Line {highlightLine}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-300 hover:text-white bg-[#1e2c4a]/60 hover:bg-[#1e2c4a] rounded transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      )}

      <div style={{ height }}>
        <Editor
          height="100%"
          language={getMonacoLang(language)}
          value={code}
          theme="vs-dark"
          onMount={handleEditorDidMount}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            folding: true,
            renderLineHighlight: 'all',
            padding: { top: 12, bottom: 12 },
          }}
          loading={
            <div className="flex items-center justify-center h-full text-slate-400 text-sm">
              Loading source viewer...
            </div>
          }
        />
      </div>
    </div>
  );
};
