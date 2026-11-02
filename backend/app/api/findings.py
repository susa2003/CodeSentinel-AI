from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.database import get_db
from app.models.entities import Finding, FindingStatusHistory, AnalysisJob
from app.schemas.finding import (
    FindingResponse,
    FindingListResponse,
    FindingStatusUpdate,
    SeverityEnum,
    CategoryEnum,
    VerificationStatusEnum
)
from app.core.config import settings
from app.core.security import is_safe_path

router = APIRouter(tags=["findings"])


@router.get("/analyses/{analysis_id}/findings", response_model=FindingListResponse)
def list_findings(
    analysis_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    severity: Optional[SeverityEnum] = None,
    category: Optional[CategoryEnum] = None,
    source_analyzer: Optional[str] = None,
    verification_status: Optional[VerificationStatusEnum] = None,
    file_path: Optional[str] = None,
    search: Optional[str] = None,
    is_ai: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Finding).filter(Finding.analysis_id == analysis_id)

    if severity:
        query = query.filter(Finding.severity == severity.value)
    if category:
        query = query.filter(Finding.category == category.value)
    if source_analyzer:
        query = query.filter(Finding.source_analyzer == source_analyzer)
    if verification_status:
        query = query.filter(Finding.verification_status == verification_status.value)
    if file_path:
        query = query.filter(Finding.file_path.ilike(f"%{file_path}%"))
    if is_ai is not None:
        query = query.filter(Finding.is_ai_suggested == is_ai)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Finding.title.ilike(search_pattern),
                Finding.explanation.ilike(search_pattern),
                Finding.rule_id.ilike(search_pattern),
                Finding.file_path.ilike(search_pattern)
            )
        )

    total = query.count()
    items = query.order_by(Finding.severity.asc(), Finding.start_line.asc()).offset((page - 1) * page_size).limit(page_size).all()

    return FindingListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[FindingResponse.model_validate(item) for item in items]
    )


@router.get("/findings/{finding_id}", response_model=FindingResponse)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse.model_validate(finding)


@router.patch("/findings/{finding_id}/status", response_model=FindingResponse)
def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdate,
    db: Session = Depends(get_db)
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.verification_status
    new_status = payload.status.value

    if old_status != new_status:
        finding.verification_status = new_status
        history_record = FindingStatusHistory(
            finding_id=finding.id,
            old_status=old_status,
            new_status=new_status,
            notes=payload.notes
        )
        db.add(history_record)
        db.commit()
        db.refresh(finding)

    return FindingResponse.model_validate(finding)


@router.get("/analyses/{analysis_id}/file-content")
def get_file_content(
    analysis_id: str,
    file_path: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Returns the file content for Monaco Editor rendering with safe path validation.
    """
    workspace = settings.EXTRACTED_DIR / analysis_id
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace files not found")

    target_file = (workspace / file_path).resolve()
    if not is_safe_path(workspace, target_file) or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found or access denied")

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {
            "file_path": file_path,
            "content": content,
            "total_lines": len(content.splitlines())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
