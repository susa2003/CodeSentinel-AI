import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { NewAnalysisPage } from './pages/NewAnalysisPage';
import { ProgressPage } from './pages/ProgressPage';
import { ResultsPage } from './pages/ResultsPage';
import { FindingsExplorerPage } from './pages/FindingsExplorerPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { DocsPage } from './pages/DocsPage';

export function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0a0f1d] text-slate-100 overflow-hidden font-sans">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/new-analysis" element={<NewAnalysisPage />} />
            <Route path="/analyses/:analysisId/progress" element={<ProgressPage />} />
            <Route path="/analyses/:analysisId" element={<ResultsPage />} />
            <Route path="/analyses/:analysisId/findings" element={<FindingsExplorerPage />} />
            <Route path="/findings" element={<FindingsExplorerPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/docs" element={<DocsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
