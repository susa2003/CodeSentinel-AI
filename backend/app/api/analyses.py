import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.entities import Project, AnalysisJob, Finding, AnalyzerRecord, FileManifestItem
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisDetailResponse,
    AnalysisProgressResponse,
    AnalysisListResponse,
    SeverityCounts,
    CategoryCounts,
    AnalyzerRecordResponse,
    FileManifestResponse
)
from app.schemas.finding import FindingResponse
from app.services.ingestion import IngestionService, IngestionError
from app.services.orchestrator import AnalysisOrchestrator

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _calculate_severity_counts(findings: List[Finding]) -> SeverityCounts:
    counts = SeverityCounts()
    for f in findings:
        sev = f.severity.upper()
        if hasattr(counts, sev):
            setattr(counts, sev, getattr(counts, sev) + 1)
    return counts


def _calculate_category_counts(findings: List[Finding]) -> CategoryCounts:
    counts = CategoryCounts()
    for f in findings:
        cat = f.category.upper()
        if hasattr(counts, cat):
            setattr(counts, cat, getattr(counts, cat) + 1)
    return counts


@router.post("", status_code=202)
async def create_analysis(
    project_name: str = Form(..., min_length=1, max_length=100),
    project_description: Optional[str] = Form(None),
    options: Optional[str] = Form("{}"),
    archive_file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Submits a ZIP project or multiple source files for automated analysis.
    """
    if not archive_file and not files:
        raise HTTPException(
            status_code=400,
            detail="Either a ZIP archive ('archive_file') or individual source files ('files') must be uploaded."
        )

    # 1. Ensure project exists
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        project = Project(name=project_name, description=project_description)
        db.add(project)
        db.commit()
        db.refresh(project)

    # 2. Parse analysis options
    try:
        options_dict = json.loads(options or "{}")
    except json.JSONDecodeError:
        options_dict = {}

    # 3. Create initial AnalysisJob
    job = AnalysisJob(
        project_id=project.id,
        status="QUEUED",
        progress_percent=0,
        current_stage="Archive Ingestion",
        stage_message="Extracting files and performing security validation",
        options=json.dumps(options_dict)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 4. Prepare workspace and extract
    workspace_dir = IngestionService.create_job_workspace(job.id)

    try:
        if archive_file and archive_file.filename and archive_file.filename.endswith(".zip"):
            temp_zip = await IngestionService.save_uploaded_zip(archive_file, job.id)
            try:
                IngestionService.inspect_and_extract_zip(temp_zip, workspace_dir)
            finally:
                temp_zip.unlink(missing_ok=True)
        elif files:
            await IngestionService.save_individual_files(files, workspace_dir)
        elif archive_file:
            # Single source file uploaded via archive_file parameter
            await IngestionService.save_individual_files([archive_file], workspace_dir)

    except IngestionError as ie:
        IngestionService.cleanup_workspace(job.id)
        job.status = "FAILED"
        job.error_message = str(ie)
        db.commit()
        raise HTTPException(status_code=400, detail=str(ie))
    except Exception as e:
        IngestionService.cleanup_workspace(job.id)
        job.status = "FAILED"
        job.error_message = f"Failed to ingest files: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    # 5. Launch asynchronous background orchestration
    asyncio.create_task(
        AnalysisOrchestrator.run_analysis(job.id, workspace_dir, options_dict)
    )

    return {
        "analysis_id": job.id,
        "project_id": project.id,
        "project_name": project.name,
        "status": job.status,
        "message": "Analysis successfully initiated in the background."
    }


@router.get("", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AnalysisJob)
    if project_id:
        query = query.filter(AnalysisJob.project_id == project_id)
    if status:
        query = query.filter(AnalysisJob.status == status.upper())

    total = query.count()
    jobs = query.order_by(AnalysisJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for j in jobs:
        try:
            langs = json.loads(j.detected_languages or "[]")
        except Exception:
            langs = []

        sev_counts = _calculate_severity_counts(j.findings)

        items.append(AnalysisResponse(
            id=j.id,
            project_id=j.project_id,
            project_name=j.project.name if j.project else "Unknown",
            status=j.status,
            progress_percent=j.progress_percent,
            current_stage=j.current_stage,
            stage_message=j.stage_message,
            error_message=j.error_message,
            created_at=j.created_at,
            started_at=j.started_at,
            completed_at=j.completed_at,
            duration_seconds=j.duration_seconds,
            total_files=j.total_files,
            total_lines=j.total_lines,
            detected_languages=langs,
            severity_counts=sev_counts,
            total_findings=len(j.findings)
        ))

    return AnalysisListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(analysis_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == analysis_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        langs = json.loads(job.detected_languages or "[]")
    except Exception:
        langs = []

    try:
        opts = json.loads(job.options or "{}")
    except Exception:
        opts = {}

    sev_counts = _calculate_severity_counts(job.findings)
    cat_counts = _calculate_category_counts(job.findings)

    analyzer_records = [
        AnalyzerRecordResponse(
            id=r.id,
            analyzer_name=r.analyzer_name,
            status=r.status,
            duration_seconds=r.duration_seconds,
            findings_count=r.findings_count,
            message=r.message,
            skip_reason=r.skip_reason
        )
        for r in job.analyzer_records
    ]

    manifest_items = [
        FileManifestResponse(
            id=m.id,
            relative_path=m.relative_path,
            language=m.language,
            lines_of_code=m.lines_of_code,
            size_bytes=m.size_bytes,
            is_test_file=m.is_test_file,
            is_entry_point=m.is_entry_point,
            has_secrets=m.has_secrets
        )
        for m in job.manifest_items
    ]

    findings = [FindingResponse.model_validate(f) for f in job.findings]

    return AnalysisDetailResponse(
        id=job.id,
        project_id=job.project_id,
        project_name=job.project.name if job.project else "Unknown",
        status=job.status,
        progress_percent=job.progress_percent,
        current_stage=job.current_stage,
        stage_message=job.stage_message,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=job.duration_seconds,
        total_files=job.total_files,
        total_lines=job.total_lines,
        detected_languages=langs,
        options=opts,
        severity_counts=sev_counts,
        category_counts=cat_counts,
        total_findings=len(findings),
        analyzer_records=analyzer_records,
        manifest_items=manifest_items,
        findings=findings
    )


@router.get("/{analysis_id}/progress", response_model=AnalysisProgressResponse)
def get_analysis_progress(analysis_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == analysis_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisProgressResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_stage=job.current_stage,
        stage_message=job.stage_message,
        error_message=job.error_message,
        total_files=job.total_files,
        total_lines=job.total_lines,
        duration_seconds=job.duration_seconds
    )


@router.delete("/{analysis_id}", status_code=200)
def delete_or_cancel_analysis(analysis_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == analysis_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if job.status in ("QUEUED", "RUNNING"):
        job.status = "CANCELLED"
        job.stage_message = "Analysis was cancelled by the user."
        db.commit()
        IngestionService.cleanup_workspace(analysis_id)
        return {"message": "Analysis cancelled successfully."}

    # If completed or failed, remove record
    IngestionService.cleanup_workspace(analysis_id)
    db.delete(job)
    db.commit()
    return {"message": "Analysis record and workspace successfully deleted."}
