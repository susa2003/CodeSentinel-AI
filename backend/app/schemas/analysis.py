from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.finding import FindingResponse, SeverityEnum, CategoryEnum


class AnalysisOptions(BaseModel):
    enable_ast: bool = True
    enable_ruff: bool = True
    enable_bandit: bool = True
    enable_pattern_engine: bool = True
    enable_cross_file: bool = True
    enable_llm_review: bool = True
    demo_mode: bool = True


class AnalysisCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100)
    project_description: Optional[str] = None
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class AnalyzerRecordResponse(BaseModel):
    id: str
    analyzer_name: str
    status: str
    duration_seconds: float
    findings_count: int
    message: Optional[str] = None
    skip_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class FileManifestResponse(BaseModel):
    id: str
    relative_path: str
    language: str
    lines_of_code: int
    size_bytes: int
    is_test_file: bool
    is_entry_point: bool
    has_secrets: bool

    model_config = {"from_attributes": True}


class SeverityCounts(BaseModel):
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0
    INFORMATIONAL: int = 0


class CategoryCounts(BaseModel):
    SECURITY: int = 0
    BUG_RISK: int = 0
    QUALITY: int = 0
    PERFORMANCE: int = 0
    MAINTAINABILITY: int = 0
    SYNTAX: int = 0
    CROSS_FILE: int = 0
    TESTING: int = 0


class AnalysisProgressResponse(BaseModel):
    id: str
    project_id: str
    status: str
    progress_percent: int
    current_stage: str
    stage_message: Optional[str] = None
    error_message: Optional[str] = None
    total_files: int
    total_lines: int
    duration_seconds: Optional[float] = None


class AnalysisResponse(BaseModel):
    id: str
    project_id: str
    project_name: Optional[str] = None
    status: str
    progress_percent: int
    current_stage: str
    stage_message: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_files: int
    total_lines: int
    detected_languages: List[str] = []
    severity_counts: SeverityCounts = Field(default_factory=SeverityCounts)
    total_findings: int = 0

    model_config = {"from_attributes": True}


class AnalysisDetailResponse(AnalysisResponse):
    options: Dict[str, Any] = {}
    severity_counts: SeverityCounts = Field(default_factory=SeverityCounts)
    category_counts: CategoryCounts = Field(default_factory=CategoryCounts)
    analyzer_records: List[AnalyzerRecordResponse] = []
    manifest_items: List[FileManifestResponse] = []
    findings: List[FindingResponse] = []


class AnalysisListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AnalysisResponse]
