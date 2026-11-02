import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    analyses = relationship("AnalysisJob", back_populates="project", cascade="all, delete-orphan", order_by="desc(AnalysisJob.created_at)")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="QUEUED", index=True, nullable=False)  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    progress_percent = Column(Integer, default=0, nullable=False)
    current_stage = Column(String(100), default="Initialized", nullable=False)
    stage_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    total_files = Column(Integer, default=0, nullable=False)
    total_lines = Column(Integer, default=0, nullable=False)
    detected_languages = Column(Text, default="[]", nullable=False)  # JSON array
    options = Column(Text, default="{}", nullable=False)  # JSON dict

    project = relationship("Project", back_populates="analyses")
    findings = relationship("Finding", back_populates="analysis", cascade="all, delete-orphan", order_by="desc(Finding.created_at)")
    analyzer_records = relationship("AnalyzerRecord", back_populates="analysis", cascade="all, delete-orphan")
    manifest_items = relationship("FileManifestItem", back_populates="analysis", cascade="all, delete-orphan")


class FileManifestItem(Base):
    __tablename__ = "file_manifest_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path = Column(String(500), nullable=False)
    language = Column(String(50), nullable=False)
    lines_of_code = Column(Integer, default=0, nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    is_test_file = Column(Boolean, default=False, nullable=False)
    is_entry_point = Column(Boolean, default=False, nullable=False)
    has_secrets = Column(Boolean, default=False, nullable=False)

    analysis = relationship("AnalysisJob", back_populates="manifest_items")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)
    source_analyzer = Column(String(50), nullable=False, index=True)  # python_ast, ruff, bandit, pattern_engine, cross_file, llm_review
    file_path = Column(String(500), nullable=False, index=True)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=True)
    severity = Column(String(20), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    confidence = Column(String(20), default="MEDIUM", nullable=False)  # HIGH, MEDIUM, LOW
    category = Column(String(50), nullable=False, index=True)  # SECURITY, BUG_RISK, QUALITY, PERFORMANCE, MAINTAINABILITY, SYNTAX, CROSS_FILE, TESTING
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    doc_url = Column(String(500), nullable=True)
    
    is_ai_suggested = Column(Boolean, default=False, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    verification_status = Column(String(30), default="UNREVIEWED", nullable=False, index=True)  # UNREVIEWED, CONFIRMED, FALSE_POSITIVE, FIXED, ACCEPTED_RISK
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    analysis = relationship("AnalysisJob", back_populates="findings")
    status_history = relationship("FindingStatusHistory", back_populates="finding", cascade="all, delete-orphan", order_by="desc(FindingStatusHistory.changed_at)")

    __table_args__ = (
        Index("idx_finding_analysis_severity", "analysis_id", "severity"),
        Index("idx_finding_analysis_category", "analysis_id", "category"),
    )


class AnalyzerRecord(Base):
    __tablename__ = "analyzer_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    analyzer_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED, SKIPPED
    duration_seconds = Column(Float, default=0.0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    message = Column(Text, nullable=True)
    skip_reason = Column(Text, nullable=True)

    analysis = relationship("AnalysisJob", back_populates="analyzer_records")


class FindingStatusHistory(Base):
    __tablename__ = "finding_status_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    finding_id = Column(String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    finding = relationship("Finding", back_populates="status_history")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
