from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.entities import Project, AnalysisJob
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse
from app.schemas.analysis import AnalysisResponse, SeverityCounts

router = APIRouter(prefix="/projects", tags=["projects"])


def _populate_project_response(p: Project, db: Session) -> ProjectResponse:
    latest_job = db.query(AnalysisJob).filter(AnalysisJob.project_id == p.id).order_by(AnalysisJob.created_at.desc()).first()
    
    latest_resp = None
    if latest_job:
        latest_resp = AnalysisResponse(
            id=latest_job.id,
            project_id=latest_job.project_id,
            project_name=p.name,
            status=latest_job.status,
            progress_percent=latest_job.progress_percent,
            current_stage=latest_job.current_stage,
            stage_message=latest_job.stage_message,
            error_message=latest_job.error_message,
            created_at=latest_job.created_at,
            started_at=latest_job.started_at,
            completed_at=latest_job.completed_at,
            duration_seconds=latest_job.duration_seconds,
            total_files=latest_job.total_files,
            total_lines=latest_job.total_lines,
            detected_languages=[],
            total_findings=len(latest_job.findings) if latest_job.findings else 0
        )

    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
        total_analyses=len(p.analyses) if p.analyses else 0,
        latest_analysis=latest_resp
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Project).filter(Project.name == data.name).first()
    if existing:
        return _populate_project_response(existing, db)

    project = Project(name=data.name, description=data.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _populate_project_response(project, db)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    projects = db.query(Project).order_by(Project.created_at.desc()).limit(limit).all()
    items = [_populate_project_response(p, db) for p in projects]
    return ProjectListResponse(total=len(items), items=items)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _populate_project_response(project, db)
