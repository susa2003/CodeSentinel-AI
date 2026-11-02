import pytest
from pathlib import Path
from app.services.scanner import ProjectScanner
from app.analyzers.python_ast import PythonASTAnalyzer
from app.analyzers.pattern_engine import PatternEngineAnalyzer

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_PY_DIR = ROOT_DIR / "sample_projects" / "vulnerable_python_app"
SAMPLE_JS_DIR = ROOT_DIR / "sample_projects" / "vulnerable_js_app"


@pytest.mark.asyncio
async def test_python_ast_analyzer_rules():
    sample_dir = SAMPLE_PY_DIR
    scan = ProjectScanner.scan_project(sample_dir)

    analyzer = PythonASTAnalyzer()
    result = await analyzer.analyze(sample_dir, scan["manifest_items"], scan["detected_languages"])

    assert result.status == "SUCCESS"
    rule_ids = {f.rule_id for f in result.findings}

    # Verify detected intentional flaws
    assert "PY-AST-001" in rule_ids  # Mutable default
    assert "PY-AST-002" in rule_ids  # Bare except
    assert "PY-AST-004" in rule_ids  # eval
    assert "PY-AST-005" in rule_ids  # os.system
    assert "PY-AST-008" in rule_ids  # MD5
    assert "PY-AST-009" in rule_ids  # SQL injection
    assert "PY-AST-011" in rule_ids  # Zero division


@pytest.mark.asyncio
async def test_polyglot_pattern_engine_rules():
    sample_dir = SAMPLE_JS_DIR
    scan = ProjectScanner.scan_project(sample_dir)

    analyzer = PatternEngineAnalyzer()
    result = await analyzer.analyze(sample_dir, scan["manifest_items"], scan["detected_languages"])

    assert result.status == "SUCCESS"
    rule_ids = {f.rule_id for f in result.findings}

    # Verify JS vulnerabilities
    assert "JS-SEC-001" in rule_ids  # eval
    assert "JS-SEC-002" in rule_ids  # innerHTML
    assert "JS-SEC-005" in rule_ids  # rejectUnauthorized: false
    assert "JS-SEC-006" in rule_ids  # __proto__
    assert "DB-SEC-001" in rule_ids  # SQLi template literal
