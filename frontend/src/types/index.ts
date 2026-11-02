export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';
export type Category = 
  | 'SECURITY' 
  | 'BUG_RISK' 
  | 'QUALITY' 
  | 'PERFORMANCE' 
  | 'MAINTAINABILITY' 
  | 'SYNTAX' 
  | 'CROSS_FILE' 
  | 'TESTING';

export type VerificationStatus = 
  | 'UNREVIEWED' 
  | 'CONFIRMED' 
  | 'FALSE_POSITIVE' 
  | 'FIXED' 
  | 'ACCEPTED_RISK';

export interface FindingStatusHistory {
  id: string;
  old_status: string;
  new_status: string;
  notes?: string;
  changed_at: string;
}

export interface Finding {
  id: string;
  analysis_id: string;
  rule_id: string;
  source_analyzer: string;
  file_path: string;
  start_line: number;
  end_line?: number;
  severity: Severity;
  confidence: Confidence;
  category: Category;
  title: string;
  explanation: string;
  evidence?: string;
  remediation?: string;
  doc_url?: string;
  is_ai_suggested: boolean;
  is_demo: boolean;
  verification_status: VerificationStatus;
  created_at?: string;
  updated_at?: string;
  status_history?: FindingStatusHistory[];
}

export interface AnalyzerRecord {
  id: string;
  analyzer_name: string;
  status: 'SUCCESS' | 'FAILED' | 'SKIPPED';
  duration_seconds: number;
  findings_count: number;
  message?: string;
  skip_reason?: string;
}

export interface FileManifestItem {
  id: string;
  relative_path: string;
  language: string;
  lines_of_code: number;
  size_bytes: number;
  is_test_file: boolean;
  is_entry_point: boolean;
  has_secrets: boolean;
}

export interface SeverityCounts {
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
  INFORMATIONAL: number;
}

export interface CategoryCounts {
  SECURITY: number;
  BUG_RISK: number;
  QUALITY: number;
  PERFORMANCE: number;
  MAINTAINABILITY: number;
  SYNTAX: number;
  CROSS_FILE: number;
  TESTING: number;
}

export interface AnalysisJob {
  id: string;
  project_id: string;
  project_name?: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  progress_percent: number;
  current_stage: string;
  stage_message?: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  total_files: number;
  total_lines: number;
  detected_languages: string[];
  severity_counts: SeverityCounts;
  total_findings: number;
}

export interface AnalysisDetail extends AnalysisJob {
  options: Record<string, any>;
  category_counts: CategoryCounts;
  analyzer_records: AnalyzerRecord[];
  manifest_items: FileManifestItem[];
  findings: Finding[];
}

export interface AnalysisProgress {
  id: string;
  project_id: string;
  status: string;
  progress_percent: number;
  current_stage: string;
  stage_message?: string;
  error_message?: string;
  total_files: number;
  total_lines: number;
  duration_seconds?: number;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  total_analyses: number;
  latest_analysis?: AnalysisJob;
}

export interface DashboardStats {
  total_projects: number;
  total_analyses: number;
  completed_analyses: number;
  failed_analyses: number;
  total_findings: number;
  findings_by_severity: Record<Severity, number>;
  findings_by_category: Record<Category, number>;
  findings_by_status: Record<VerificationStatus, number>;
  top_vulnerable_files: { file_path: string; count: number }[];
  recent_analyses: {
    id: string;
    project_name: string;
    status: string;
    created_at: string;
    duration_seconds?: number;
    total_files: number;
    total_lines: number;
    total_findings: number;
  }[];
  is_empty: boolean;
}

export interface SystemSettings {
  settings: Record<string, any>;
  environment: string;
  active_llm_provider: string;
  llm_has_api_key: boolean;
  installed_analyzers: Record<string, boolean>;
}

export interface LLMTestResponse {
  success: boolean;
  provider: string;
  message: string;
  latency_ms?: number;
  is_demo_mode: boolean;
}
