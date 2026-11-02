from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.analysis import AnalysisResponse


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime
    total_analyses: int = 0
    latest_analysis: Optional[AnalysisResponse] = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    total: int
    items: List[ProjectResponse]
