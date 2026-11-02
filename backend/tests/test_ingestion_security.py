import io
import zipfile
import pytest
from pathlib import Path

from app.core.security import is_safe_path, validate_archive_entry_name
from app.services.ingestion import IngestionService, IngestionError


def test_validate_archive_entry_name():
    # Valid relative entries
    assert validate_archive_entry_name("app/main.py")[0] is True
    assert validate_archive_entry_name("src/utils/helpers.js")[0] is True

    # Path traversal rejection
    assert validate_archive_entry_name("../etc/passwd")[0] is False
    assert validate_archive_entry_name("app/../../secret.txt")[0] is False

    # Absolute path rejection
    assert validate_archive_entry_name("/root/.ssh/id_rsa")[0] is False
    assert validate_archive_entry_name("C:/Windows/System32/cmd.exe")[0] is False
    assert validate_archive_entry_name("D:\\Windows\\cmd.exe")[0] is False

    # Null byte injection
    assert validate_archive_entry_name("valid.py\0malicious.sh")[0] is False


def test_is_safe_path(tmp_path):
    base_dir = tmp_path / "workspace"
    base_dir.mkdir()

    safe_target = base_dir / "src" / "index.js"
    assert is_safe_path(base_dir, safe_target) is True

    escaped_target = base_dir / ".." / "outside.txt"
    assert is_safe_path(base_dir, escaped_target) is False


def test_zipslip_traversal_rejection(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("../../malicious.py", "print('hacked')")

    zip_bytes.seek(0)
    zip_path = tmp_path / "traversal.zip"
    zip_path.write_bytes(zip_bytes.getvalue())

    target_dir = tmp_path / "extracted"
    target_dir.mkdir()

    with pytest.raises(IngestionError) as exc_info:
        IngestionService.inspect_and_extract_zip(zip_path, target_dir)

    assert "Directory traversal" in str(exc_info.value) or "Security validation failed" in str(exc_info.value)


def test_valid_zip_extraction(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("app/main.py", "def hello(): pass")
        zf.writestr("app/utils.py", "def add(a, b): return a + b")

    zip_bytes.seek(0)
    zip_path = tmp_path / "valid.zip"
    zip_path.write_bytes(zip_bytes.getvalue())

    target_dir = tmp_path / "extracted_valid"
    target_dir.mkdir()

    count, total_size = IngestionService.inspect_and_extract_zip(zip_path, target_dir)
    assert count == 2
    assert (target_dir / "app" / "main.py").exists()
    assert (target_dir / "app" / "utils.py").exists()
