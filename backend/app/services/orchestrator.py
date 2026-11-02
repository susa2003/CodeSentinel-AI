import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.entities import AnalysisJob, FileManifestItem, Finding, AnalyzerRecord
from app.schemas.analysis import AnalysisOptions
from app.services.scanner import ProjectScanner
from app.services.cross_file import CrossFileAnalyzer, select_targeted_context_for_llm
from app.services.llm_service import LLMReviewService
from app.analyzers.python_ast import PythonASTAnalyzer
from app.analyzers.ruff_adapter import RuffAnalyzer
from app.analyzers.bandit_adapter import BanditAnalyzer
from app.analyzers.pattern_engine import PatternEngineAnalyzer
from app.analyzers.semgrep_adapter import SemgrepAnalyzer
from app.analyzers.base import NormalizedFinding


class AnalysisOrchestrator:
    @staticmethod
    def _is_cancelled(job_id: str, db: Session) -> bool:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        return job is not None and job.status == "CANCELLED"

    @classmethod
    async def run_analysis(cls, job_id: str, project_dir: Path, options_dict: Dict[str, Any]):
        """
        Background task executing end-to-end analysis.
        """
        db = SessionLocal()
        start_time = time.time()

        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if not job:
                return

            job.status = "RUNNING"
            job.started_at = datetime.utcnow()
            job.progress_percent = 5
            job.current_stage = "Scanning files and building manifest"
            job.stage_message = "Building file list, detecting languages, checking file structures"
            db.commit()

            options = AnalysisOptions(**options_dict)

            # Stage 1: Manifest & Language Scan
            scan_results = ProjectScanner.scan_project(project_dir)
            
            if cls._is_cancelled(job_id, db):
                return

            job.total_files = scan_results["total_files"]
            job.total_lines = scan_results["total_loc"]
            job.detected_languages = json.dumps(scan_results["detected_languages"])
            job.progress_percent = 20
            job.current_stage = "File manifest generated"
            job.stage_message = f"Identified {scan_results['total_files']} files ({scan_results['total_loc']} LOC)"
            db.commit()

            # Save manifest items to DB
            manifest_records = []
            for item in scan_results["manifest_items"]:
                manifest_records.append(FileManifestItem(
                    analysis_id=job_id,
                    relative_path=item["relative_path"],
                    language=item["language"],
                    lines_of_code=item["lines_of_code"],
                    size_bytes=item["size_bytes"],
                    is_test_file=item["is_test_file"],
                    is_entry_point=item["is_entry_point"],
                    has_secrets=item["has_secrets"]
                ))
            db.bulk_save_objects(manifest_records)
            db.commit()

            all_findings: List[NormalizedFinding] = []
            analyzer_records: List[AnalyzerRecord] = []

            # Stage 2: Static Analyzers
            if cls._is_cancelled(job_id, db):
                return

            job.progress_percent = 35
            job.current_stage = "Executing static analysis engines"
            job.stage_message = "Running AST analysis, Ruff, Bandit, and Pattern detectors"
            db.commit()

            analyzers_to_run = []
            if options.enable_ast:
                analyzers_to_run.append(PythonASTAnalyzer())
            if options.enable_pattern_engine:
                analyzers_to_run.append(PatternEngineAnalyzer())
            if options.enable_ruff:
                analyzers_to_run.append(RuffAnalyzer())
            if options.enable_bandit:
                analyzers_to_run.append(BanditAnalyzer())
            analyzers_to_run.append(SemgrepAnalyzer())

            for analyzer in analyzers_to_run:
                if cls._is_cancelled(job_id, db):
                    return
                try:
                    res = await analyzer.analyze(
                        project_dir,
                        scan_results["manifest_items"],
                        scan_results["detected_languages"]
                    )
                    all_findings.extend(res.findings)
                    analyzer_records.append(AnalyzerRecord(
                        analysis_id=job_id,
                        analyzer_name=res.analyzer_name,
                        status=res.status,
                        duration_seconds=res.duration_seconds,
                        findings_count=len(res.findings),
                        message=res.message,
                        skip_reason=res.skip_reason
                    ))
                except Exception as ex:
                    analyzer_records.append(AnalyzerRecord(
                        analysis_id=job_id,
                        analyzer_name=analyzer.name,
                        status="FAILED",
                        duration_seconds=0.0,
                        findings_count=0,
                        message=str(ex).strip() or type(ex).__name__
                    ))

            # Stage 3: Cross-File Analysis
            if cls._is_cancelled(job_id, db):
                return

            if options.enable_cross_file:
                job.progress_percent = 60
                job.current_stage = "Analyzing cross-file relationships"
                job.stage_message = "Building module dependency graph and verifying cross-module imports"
                db.commit()

                cross_analyzer = CrossFileAnalyzer()
                cross_res = await cross_analyzer.analyze(
                    project_dir,
                    scan_results["manifest_items"],
                    scan_results["detected_languages"]
                )
                all_findings.extend(cross_res.findings)
                analyzer_records.append(AnalyzerRecord(
                    analysis_id=job_id,
                    analyzer_name=cross_res.analyzer_name,
                    status=cross_res.status,
                    duration_seconds=cross_res.duration_seconds,
                    findings_count=len(cross_res.findings),
                    message=cross_res.message,
                    skip_reason=cross_res.skip_reason
                ))

            # Stage 4: AI Review & Heuristic Review
            if cls._is_cancelled(job_id, db):
                return

            if options.enable_llm_review:
                job.progress_percent = 80
                job.current_stage = "Performing AI-assisted code review"
                job.stage_message = "Selecting targeted high-risk context and evaluating logic flaws"
                db.commit()

                targeted_ctx = select_targeted_context_for_llm(
                    project_dir,
                    scan_results["manifest_items"],
                    all_findings,
                    max_tokens=settings.LLM_MAX_CONTEXT_TOKENS
                )

                llm_findings, llm_msg, is_demo = await LLMReviewService.run_review(
                    project_dir,
                    targeted_ctx,
                    scan_results["manifest_items"],
                    force_demo=options.demo_mode
                )
                all_findings.extend(llm_findings)
                analyzer_records.append(AnalyzerRecord(
                    analysis_id=job_id,
                    analyzer_name="llm_review",
                    status="SUCCESS" if llm_findings or "success" in llm_msg.lower() or is_demo else "FAILED",
                    duration_seconds=1.5,
                    findings_count=len(llm_findings),
                    message=llm_msg,
                    skip_reason=None
                ))

            # Stage 5: Deduplication & Persistence
            if cls._is_cancelled(job_id, db):
                return

            job.progress_percent = 95
            job.current_stage = "Finalizing findings and summary metrics"
            job.stage_message = "Deduplicating findings and persisting records"
            db.commit()

            # Save analyzer execution records
            for rec in analyzer_records:
                db.add(rec)
            db.commit()

            # Deduplicate findings
            seen_signatures = set()
            unique_findings: List[Finding] = []

            for f in all_findings:
                sig = (f.file_path, f.start_line, f.rule_id, f.title)
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)

                finding_record = Finding(
                    analysis_id=job_id,
                    rule_id=f.rule_id,
                    source_analyzer=f.source_analyzer,
                    file_path=f.file_path,
                    start_line=f.start_line,
                    end_line=f.end_line,
                    severity=f.severity.value,
                    confidence=f.confidence.value,
                    category=f.category.value,
                    title=f.title,
                    explanation=f.explanation,
                    evidence=f.evidence,
                    remediation=f.remediation,
                    doc_url=f.doc_url,
                    is_ai_suggested=f.is_ai_suggested,
                    is_demo=f.is_demo,
                    verification_status=f.verification_status.value
                )
                unique_findings.append(finding_record)

            db.bulk_save_objects(unique_findings)

            # Finalize Job Record
            duration = round(time.time() - start_time, 2)
            job.status = "COMPLETED"
            job.progress_percent = 100
            job.current_stage = "Analysis Completed"
            job.stage_message = f"Successfully generated {len(unique_findings)} findings across {job.total_files} files."
            job.completed_at = datetime.utcnow()
            job.duration_seconds = duration
            db.commit()

        except Exception as e:
            if not cls._is_cancelled(job_id, db):
                job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
                if job:
                    job.status = "FAILED"
                    job.progress_percent = 100
                    job.current_stage = "Analysis Failed"
                    job.error_message = f"Internal analysis error: {str(e)}"
                    job.completed_at = datetime.utcnow()
                    job.duration_seconds = round(time.time() - start_time, 2)
                    db.commit()
        finally:
            db.close()
