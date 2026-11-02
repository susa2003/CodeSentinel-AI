import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.entities import Project, AnalysisJob, Finding

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Computes real metrics strictly from database records.
    """
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_analyses = db.query(func.count(AnalysisJob.id)).scalar() or 0
    completed_analyses = db.query(func.count(AnalysisJob.id)).filter(AnalysisJob.status == "COMPLETED").scalar() or 0
    failed_analyses = db.query(func.count(AnalysisJob.id)).filter(AnalysisJob.status == "FAILED").scalar() or 0
    total_findings = db.query(func.count(Finding.id)).scalar() or 0

    # Severity distribution
    sev_query = db.query(Finding.severity, func.count(Finding.id)).group_by(Finding.severity).all()
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}
    for sev, cnt in sev_query:
        if sev in sev_counts:
            sev_counts[sev] = cnt

    # Category distribution
    cat_query = db.query(Finding.category, func.count(Finding.id)).group_by(Finding.category).all()
    cat_counts = {}
    for cat, cnt in cat_query:
        cat_counts[cat] = cnt

    # Status distribution
    status_query = db.query(Finding.verification_status, func.count(Finding.id)).group_by(Finding.verification_status).all()
    status_counts = {}
    for st, cnt in status_query:
        status_counts[st] = cnt

    # Top vulnerable files
    top_files_query = (
        db.query(Finding.file_path, func.count(Finding.id).label("count"))
        .group_by(Finding.file_path)
        .order_by(func.count(Finding.id).desc())
        .limit(5)
        .all()
    )
    top_files = [{"file_path": row[0], "count": row[1]} for row in top_files_query]

    # Recent analyses
    recent_jobs = (
        db.query(AnalysisJob)
        .order_by(AnalysisJob.created_at.desc())
        .limit(5)
        .all()
    )
    recent_analyses = []
    for j in recent_jobs:
        recent_analyses.append({
            "id": j.id,
            "project_name": j.project.name if j.project else "Unknown",
            "status": j.status,
            "created_at": j.created_at.isoformat(),
            "duration_seconds": j.duration_seconds,
            "total_files": j.total_files,
            "total_lines": j.total_lines,
            "total_findings": len(j.findings) if j.findings else 0
        })

    return {
        "total_projects": total_projects,
        "total_analyses": total_analyses,
        "completed_analyses": completed_analyses,
        "failed_analyses": failed_analyses,
        "total_findings": total_findings,
        "findings_by_severity": sev_counts,
        "findings_by_category": cat_counts,
        "findings_by_status": status_counts,
        "top_vulnerable_files": top_files,
        "recent_analyses": recent_analyses,
        "is_empty": total_analyses == 0
    }
