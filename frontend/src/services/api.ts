import axios from 'axios';
import {
  DashboardStats,
  Project,
  AnalysisJob,
  AnalysisDetail,
  AnalysisProgress,
  Finding,
  VerificationStatus,
  SystemSettings,
  LLMTestResponse
} from '../types';

const API_BASE = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Stats
  async getDashboardStats(): Promise<DashboardStats> {
    const res = await apiClient.get<DashboardStats>('/stats/dashboard');
    return res.data;
  },

  // Projects
  async listProjects(): Promise<{ total: number; items: Project[] }> {
    const res = await apiClient.get<{ total: number; items: Project[] }>('/projects');
    return res.data;
  },

  async createProject(name: string, description?: string): Promise<Project> {
    const res = await apiClient.post<Project>('/projects', { name, description });
    return res.data;
  },

  async getProject(id: string): Promise<Project> {
    const res = await apiClient.get<Project>(`/projects/${id}`);
    return res.data;
  },

  // Analyses
  async createAnalysis(formData: FormData, onUploadProgress?: (progressEvent: any) => void): Promise<{ analysis_id: string; project_id: string; project_name: string; status: string }> {
    const res = await apiClient.post('/analyses', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return res.data;
  },

  async listAnalyses(params?: { page?: number; page_size?: number; project_id?: string; status?: string }): Promise<{ total: number; page: number; page_size: number; items: AnalysisJob[] }> {
    const res = await apiClient.get('/analyses', { params });
    return res.data;
  },

  async getAnalysisDetail(analysisId: string): Promise<AnalysisDetail> {
    const res = await apiClient.get<AnalysisDetail>(`/analyses/${analysisId}`);
    return res.data;
  },

  async getAnalysisProgress(analysisId: string): Promise<AnalysisProgress> {
    const res = await apiClient.get<AnalysisProgress>(`/analyses/${analysisId}/progress`);
    return res.data;
  },

  async deleteOrCancelAnalysis(analysisId: string): Promise<{ message: string }> {
    const res = await apiClient.delete(`/analyses/${analysisId}`);
    return res.data;
  },

  // Findings
  async listFindings(analysisId: string, params?: Record<string, any>): Promise<{ total: number; page: number; page_size: number; items: Finding[] }> {
    const res = await apiClient.get(`/analyses/${analysisId}/findings`, { params });
    return res.data;
  },

  async updateFindingStatus(findingId: string, status: VerificationStatus, notes?: string): Promise<Finding> {
    const res = await apiClient.patch<Finding>(`/findings/${findingId}/status`, { status, notes });
    return res.data;
  },

  async getFileContent(analysisId: string, filePath: string): Promise<{ file_path: string; content: string; total_lines: number }> {
    const res = await apiClient.get(`/analyses/${analysisId}/file-content`, {
      params: { file_path: filePath },
    });
    return res.data;
  },

  // Reports
  getReportDownloadUrl(analysisId: string, format: 'json' | 'html' | 'markdown'): string {
    return `${API_BASE}/analyses/${analysisId}/report?format=${format}&download=true`;
  },

  async getReportContent(analysisId: string, format: 'json' | 'html' | 'markdown'): Promise<string | object> {
    const res = await apiClient.get(`/analyses/${analysisId}/report`, {
      params: { format, download: false },
    });
    return res.data;
  },

  // Settings
  async getSystemSettings(): Promise<SystemSettings> {
    const res = await apiClient.get<SystemSettings>('/settings');
    return res.data;
  },

  async updateSystemSettings(payload: Record<string, any>): Promise<{ message: string }> {
    const res = await apiClient.patch('/settings', payload);
    return res.data;
  },

  async testLLM(payload: { provider: string; api_key?: string; api_base?: string; model?: string }): Promise<LLMTestResponse> {
    const res = await apiClient.post<LLMTestResponse>('/settings/test-llm', payload);
    return res.data;
  },
};
