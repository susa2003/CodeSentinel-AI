from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.entities import AnalysisJob, Project
from app.services.report_generator import ReportGenerator

router = APIRouter(tags=["reports"])


@router.get("/analyses/{analysis_id}/report")
def export_report(
    analysis_id: str,
    format: str = Query("json", pattern="^(json|html|markdown)$"),
    download: bool = Query(False),
    db: Session = Depends(get_db)
):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == analysis_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis not found")

    project_name = job.project.name if job.project else "Project"

    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}
    findings_list = []
    for f in job.findings:
        sev = f.severity.upper()
        if sev in sev_counts:
            sev_counts[sev] += 1
        findings_list.append({
            "id": f.id,
            "rule_id": f.rule_id,
            "source_analyzer": f.source_analyzer,
            "file_path": f.file_path,
            "start_line": f.start_line,
            "end_line": f.end_line,
            "severity": f.severity,
            "confidence": f.confidence,
            "category": f.category,
            "title": f.title,
            "explanation": f.explanation,
            "evidence": f.evidence,
            "remediation": f.remediation,
            "is_ai_suggested": f.is_ai_suggested,
            "is_demo": f.is_demo,
            "verification_status": f.verification_status,
        })

    analyzer_records = [
        {
            "analyzer_name": r.analyzer_name,
            "status": r.status,
            "duration_seconds": r.duration_seconds,
            "findings_count": r.findings_count,
            "message": r.message,
            "skip_reason": r.skip_reason
        }
        for r in job.analyzer_records
    ]

    report_payload = {
        "analysis_id": job.id,
        "project_name": project_name,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_files": job.total_files,
        "total_lines": job.total_lines,
        "duration_seconds": job.duration_seconds,
        "total_findings": len(findings_list),
        "findings_by_severity": sev_counts,
        "analyzer_records": analyzer_records,
        "findings": findings_list
    }

    safe_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")) or "project"

    if format == "html":
        content = ReportGenerator.generate_html_report(report_payload)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="codesentinel-report-{safe_name}.html"'
        return Response(content=content, media_type="text/html", headers=headers)

    elif format == "markdown":
        content = ReportGenerator.generate_markdown_report(report_payload)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="codesentinel-report-{safe_name}.md"'
        return Response(content=content, media_type="text/markdown", headers=headers)

    else:
        content = ReportGenerator.generate_json_report(report_payload)
        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="codesentinel-report-{safe_name}.json"'
        return Response(content=content, media_type="application/json", headers=headers)
