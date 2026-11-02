import pytest
from pathlib import Path
from app.services.scanner import ProjectScanner
from app.services.cross_file import CrossFileAnalyzer

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_PY_DIR = ROOT_DIR / "sample_projects" / "vulnerable_python_app"


@pytest.mark.asyncio
async def test_cross_file_missing_symbol_detection():
    sample_dir = SAMPLE_PY_DIR
    scan = ProjectScanner.scan_project(sample_dir)

    analyzer = CrossFileAnalyzer()
    res = await analyzer.analyze(sample_dir, scan["manifest_items"], scan["detected_languages"])

    assert res.status == "SUCCESS"
    missing_symbol_findings = [f for f in res.findings if f.rule_id == "CROSS-001"]
    assert len(missing_symbol_findings) > 0
    assert any("verify_jwt" in f.title for f in missing_symbol_findings)


@pytest.mark.asyncio
async def test_cross_file_circular_dependency(tmp_path):
    (tmp_path / "module_a.py").write_text("import module_b\ndef func_a(): pass\n")
    (tmp_path / "module_b.py").write_text("import module_a\ndef func_b(): pass\n")

    scan = ProjectScanner.scan_project(tmp_path)
    analyzer = CrossFileAnalyzer()
    res = await analyzer.analyze(tmp_path, scan["manifest_items"], scan["detected_languages"])

    cycle_findings = [f for f in res.findings if f.rule_id == "CROSS-002"]
    assert len(cycle_findings) > 0
