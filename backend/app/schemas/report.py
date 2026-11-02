from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ReportExportResponse(BaseModel):
    analysis_id: str
    project_name: str
    generated_at: str
    format: str  # "json", "html", "markdown"
    content: str
    total_findings: int
    findings_by_severity: Dict[str, int]
