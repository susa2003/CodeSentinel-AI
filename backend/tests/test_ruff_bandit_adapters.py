import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from app.analyzers.ruff_adapter import RuffAnalyzer
from app.analyzers.bandit_adapter import BanditAnalyzer
from app.analyzers.semgrep_adapter import SemgrepAnalyzer
from app.core.config import settings
from app.services.scanner import ProjectScanner
from app.schemas.finding import SeverityEnum, CategoryEnum

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_PY_DIR = ROOT_DIR / "sample_projects" / "vulnerable_python_app"


@pytest.fixture
def sample_manifest():
    scan = ProjectScanner.scan_project(SAMPLE_PY_DIR)
    return scan["manifest_items"]


# -----------------------------------------------------------------------------
# 1. Successful Execution Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ruff_successful_execution(sample_manifest):
    analyzer = RuffAnalyzer()
    assert analyzer.is_available() is True

    result = await analyzer.analyze(
        project_dir=SAMPLE_PY_DIR,
        manifest_items=sample_manifest,
        detected_languages=["Python"]
    )

    assert result.status == "SUCCESS"
    assert result.analyzer_name == "ruff"
    assert result.duration_seconds > 0
    assert len(result.findings) > 0
    assert "findings" in result.message.lower() or "issues" in result.message.lower()

    # Verify structure of findings
    for finding in result.findings:
        assert finding.source_analyzer == "ruff"
        assert finding.rule_id.startswith("RUFF-")
        assert finding.start_line >= 1
        assert finding.file_path in ("auth.py", "data_processor.py", "main.py") or finding.file_path.endswith(".py")
        assert isinstance(finding.severity, SeverityEnum)
        assert isinstance(finding.category, CategoryEnum)
        assert finding.title.startswith("[")

    # Check for specific expected findings in the sample app
    rule_ids = [f.rule_id for f in result.findings]
    assert any("E722" in r for r in rule_ids)  # bare except in auth.py
    assert any("B006" in r for r in rule_ids)  # mutable default in data_processor.py


@pytest.mark.asyncio
async def test_bandit_successful_execution(sample_manifest):
    analyzer = BanditAnalyzer()
    assert analyzer.is_available() is True

    result = await analyzer.analyze(
        project_dir=SAMPLE_PY_DIR,
        manifest_items=sample_manifest,
        detected_languages=["Python"]
    )

    assert result.status == "SUCCESS"
    assert result.analyzer_name == "bandit"
    assert result.duration_seconds > 0
    assert len(result.findings) >= 4  # sample app has at least 5 security flaws

    # Verify structure of findings
    for finding in result.findings:
        assert finding.source_analyzer == "bandit"
        assert finding.rule_id.startswith("BANDIT-")
        assert finding.start_line >= 1
        assert finding.category == CategoryEnum.SECURITY
        assert finding.evidence is not None

    rule_ids = [f.rule_id for f in result.findings]
    assert "BANDIT-B608" in rule_ids  # SQL Injection in auth.py
    assert "BANDIT-B605" in rule_ids  # Shell command injection in auth.py
    assert "BANDIT-B307" in rule_ids or "BANDIT-B324" in rule_ids  # eval / md5 in data_processor.py

    # Verify SQL injection severity escalation to CRITICAL
    sqli_finding = next(f for f in result.findings if f.rule_id == "BANDIT-B608")
    assert sqli_finding.severity == SeverityEnum.CRITICAL


# -----------------------------------------------------------------------------
# 2. Missing Executable & Skipped Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ruff_skipped_when_unavailable(sample_manifest):
    analyzer = RuffAnalyzer()
    with patch.object(analyzer, "is_available", return_value=False):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert result.status == "SKIPPED"
        assert "not installed" in result.skip_reason.lower()


@pytest.mark.asyncio
async def test_bandit_skipped_when_unavailable(sample_manifest):
    analyzer = BanditAnalyzer()
    with patch.object(analyzer, "is_available", return_value=False):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert result.status == "SKIPPED"
        assert "not installed" in result.skip_reason.lower()


@pytest.mark.asyncio
async def test_analyzers_skipped_for_non_python_project(sample_manifest):
    ruff = RuffAnalyzer()
    res_ruff = await ruff.analyze(SAMPLE_PY_DIR, sample_manifest, ["JavaScript"])
    assert res_ruff.status == "SKIPPED"
    assert "No Python files" in res_ruff.skip_reason

    bandit = BanditAnalyzer()
    res_bandit = await bandit.analyze(SAMPLE_PY_DIR, sample_manifest, ["JavaScript"])
    assert res_bandit.status == "SKIPPED"
    assert "No Python files" in res_bandit.skip_reason


@pytest.mark.asyncio
async def test_analyzers_handle_filenotfound_error(sample_manifest):
    analyzer = RuffAnalyzer()
    with patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file or directory", "ruff")):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert result.status == "FAILED"
        assert "executable not found" in result.message.lower()

    bandit = BanditAnalyzer()
    with patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file or directory", "bandit")):
        res_bandit = await bandit.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert res_bandit.status == "FAILED"
        assert "executable not found" in res_bandit.message.lower()


# -----------------------------------------------------------------------------
# 3. Non-Zero Exit Code and Secret Redaction Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ruff_nonzero_exit_code_with_secrets_redacted(sample_manifest):
    analyzer = RuffAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 2
    fake_completed.stdout = ""
    fake_completed.stderr = "Fatal error: crashed with API key sk-live-9876543210abcdef9876543210abcdef and token ghp_abcdefghijklmnopqrstuvwx123456"

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "exit code 2" in result.message
    # Ensure sensitive credentials were redacted and not exposed
    assert "9876543210abcdef" not in result.message
    assert "ghp_abcdefghijkl" not in result.message
    assert "REDACTED" in result.message


@pytest.mark.asyncio
async def test_bandit_nonzero_exit_code_with_secrets_redacted(sample_manifest):
    analyzer = BanditAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 1
    fake_completed.stdout = ""
    fake_completed.stderr = "Bandit error: failed parsing configuration with secret_token=ghp_abcdefghijklmnopqrstuvwx123456"

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "exit code 1" in result.message
    # Ensure sensitive credentials were redacted and not exposed
    assert "ghp_abcdefghijkl" not in result.message
    assert "REDACTED" in result.message


# -----------------------------------------------------------------------------
# 4. Malformed Output Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ruff_malformed_json_output(sample_manifest):
    analyzer = RuffAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = "This is not JSON: <html>502 Bad Gateway</html>"
    fake_completed.stderr = ""

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "Failed to parse Ruff JSON output" in result.message


@pytest.mark.asyncio
async def test_ruff_unexpected_json_structure(sample_manifest):
    analyzer = RuffAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = '{"unexpected": "object instead of list"}'
    fake_completed.stderr = ""

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "expected list of findings" in result.message


@pytest.mark.asyncio
async def test_bandit_malformed_json_output(sample_manifest):
    analyzer = BanditAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = "SyntaxError: unexpected EOF while parsing"
    fake_completed.stderr = ""

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "Failed to parse Bandit JSON output" in result.message


@pytest.mark.asyncio
async def test_bandit_unexpected_json_structure(sample_manifest):
    analyzer = BanditAnalyzer()
    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = '[1, 2, 3]'  # List instead of dict
    fake_completed.stderr = ""

    with patch("subprocess.run", return_value=fake_completed):
        result = await analyzer.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])

    assert result.status == "FAILED"
    assert "expected JSON object" in result.message


# -----------------------------------------------------------------------------
# 5. Subprocess Timeout and Directory Edge Cases
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyzers_subprocess_timeout(sample_manifest):
    ruff = RuffAnalyzer()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["ruff"], timeout=30)):
        res_ruff = await ruff.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert res_ruff.status == "FAILED"
        assert "timed out" in res_ruff.message.lower()

    bandit = BanditAnalyzer()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["bandit"], timeout=30)):
        res_bandit = await bandit.analyze(SAMPLE_PY_DIR, sample_manifest, ["Python"])
        assert res_bandit.status == "FAILED"
        assert "timed out" in res_bandit.message.lower()


@pytest.mark.asyncio
async def test_analyzers_nonexistent_directory(tmp_path, sample_manifest):
    nonexistent = tmp_path / "does_not_exist_dir"
    ruff = RuffAnalyzer()
    res_ruff = await ruff.analyze(nonexistent, sample_manifest, ["Python"])
    assert res_ruff.status == "FAILED"
    assert "does not exist" in res_ruff.message

    bandit = BanditAnalyzer()
    res_bandit = await bandit.analyze(nonexistent, sample_manifest, ["Python"])
    assert res_bandit.status == "FAILED"
    assert "does not exist" in res_bandit.message


# -----------------------------------------------------------------------------
# 6. End-to-End Orchestrator Integration Test
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_pipeline_with_ruff_and_bandit(db):
    from app.models.entities import Project, AnalysisJob, AnalyzerRecord, Finding
    from app.services.orchestrator import AnalysisOrchestrator
    from tests.conftest import TestingSessionLocal

    # Create test project and job
    project = Project(name="test-ruff-bandit-integration", description="E2E test project")
    db.add(project)
    db.commit()

    job = AnalysisJob(
        project_id=project.id,
        status="QUEUED",
        progress_percent=0,
        options='{"enable_ruff": true, "enable_bandit": true, "enable_llm_review": false}'
    )
    db.add(job)
    db.commit()
    job_id = job.id

    # Run the full orchestrator analysis
    options_dict = {
        "enable_ruff": True,
        "enable_bandit": True,
        "enable_ast": True,
        "enable_pattern": True,
        "enable_cross_file": False,
        "enable_llm_review": False,
        "demo_mode": False
    }

    # Run the full orchestrator analysis using test DB connection
    session_factory = lambda: TestingSessionLocal(bind=db.get_bind())
    with patch("app.services.orchestrator.SessionLocal", session_factory):
        await AnalysisOrchestrator.run_analysis(job_id, SAMPLE_PY_DIR, options_dict)

    # Re-query the job and records
    verify_db = session_factory()
    try:
        completed_job = verify_db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        assert completed_job is not None
        assert completed_job.status == "COMPLETED"
        assert completed_job.progress_percent == 100

        # Verify AnalyzerRecords
        records = verify_db.query(AnalyzerRecord).filter(AnalyzerRecord.analysis_id == job_id).all()
        record_map = {r.analyzer_name: r for r in records}

        # Check Ruff analyzer record
        assert "ruff" in record_map
        assert record_map["ruff"].status == "SUCCESS"
        assert record_map["ruff"].findings_count > 0
        assert record_map["ruff"].duration_seconds > 0
        assert "ruff" in record_map["ruff"].message.lower()

        # Check Bandit analyzer record
        assert "bandit" in record_map
        assert record_map["bandit"].status == "SUCCESS"
        assert record_map["bandit"].findings_count > 0
        assert record_map["bandit"].duration_seconds > 0
        assert "bandit" in record_map["bandit"].message.lower()

        # Verify Findings in database
        db_findings = verify_db.query(Finding).filter(Finding.analysis_id == job_id).all()
        ruff_findings = [f for f in db_findings if f.source_analyzer == "ruff"]
        bandit_findings = [f for f in db_findings if f.source_analyzer == "bandit"]

        assert len(ruff_findings) > 0
        assert len(bandit_findings) > 0
    finally:
        verify_db.close()

