from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class ConfidenceEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CategoryEnum(str, Enum):
    SECURITY = "SECURITY"
    BUG_RISK = "BUG_RISK"
    QUALITY = "QUALITY"
    PERFORMANCE = "PERFORMANCE"
    MAINTAINABILITY = "MAINTAINABILITY"
    SYNTAX = "SYNTAX"
    CROSS_FILE = "CROSS_FILE"
    TESTING = "TESTING"


class VerificationStatusEnum(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FIXED = "FIXED"
    ACCEPTED_RISK = "ACCEPTED_RISK"


class FindingStatusUpdate(BaseModel):
    status: VerificationStatusEnum
    notes: Optional[str] = Field(None, description="Optional notes explaining status change")


class FindingStatusHistoryResponse(BaseModel):
    id: str
    old_status: str
    new_status: str
    notes: Optional[str] = None
    changed_at: datetime

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: str
    analysis_id: str
    rule_id: str
    source_analyzer: str
    file_path: str
    start_line: int
    end_line: Optional[int] = None
    severity: SeverityEnum
    confidence: ConfidenceEnum
    category: CategoryEnum
    title: str
    explanation: str
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    doc_url: Optional[str] = None
    is_ai_suggested: bool
    is_demo: bool
    verification_status: VerificationStatusEnum
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status_history: List[FindingStatusHistoryResponse] = []

    model_config = {"from_attributes": True}


class FindingListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[FindingResponse]
