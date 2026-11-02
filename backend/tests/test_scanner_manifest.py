from pathlib import Path
from app.services.scanner import ProjectScanner
from app.core.security import redact_secrets, detect_secrets_in_text

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_PY_DIR = ROOT_DIR / "sample_projects" / "vulnerable_python_app"


def test_project_scanner_on_sample_app():
    sample_dir = SAMPLE_PY_DIR
    assert sample_dir.exists()

    scan = ProjectScanner.scan_project(sample_dir)
    assert scan["total_files"] >= 3
    assert "Python" in scan["detected_languages"]
    assert any("main.py" in ep for ep in scan["entry_points"])
    assert any("test_auth.py" in tf for tf in scan["test_files"])
    assert len(scan["secrets_detected"]) > 0


def test_secret_redaction():
    raw_snippet = 'api_key = "sk-live-9876543210abcdef9876543210abcdef"'
    redacted = redact_secrets(raw_snippet)
    assert "9876543210abcdef" not in redacted
    assert "REDACTED" in redacted


def test_exclusion_directories(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.py").write_text("print(1)")

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.py").write_text("print(2)")

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "git_internal.py").write_text("print(3)")

    scan = ProjectScanner.scan_project(tmp_path)
    rel_paths = [item["relative_path"] for item in scan["manifest_items"]]

    assert "src/index.py" in rel_paths
    assert not any("node_modules" in p for p in rel_paths)
    assert not any(".git" in p for p in rel_paths)
