from pathlib import Path
from app.services.llm_service import LLMReviewService


def test_hallucination_guard_validation(tmp_path):
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("line 1\nline 2\nline 3\n")

    # 1. Non-existent file
    is_valid, msg = LLMReviewService.validate_reference(
        tmp_path, "phantom_file.py", 1, 1, "print(1)"
    )
    assert is_valid is False
    assert "Hallucinated file" in msg

    # 2. Out of bounds line number
    is_valid, msg = LLMReviewService.validate_reference(
        tmp_path, "valid.py", 999, 999, "print(1)"
    )
    assert is_valid is False
    assert "Invalid start_line" in msg

    # 3. Valid file and line number
    is_valid, msg = LLMReviewService.validate_reference(
        tmp_path, "valid.py", 2, 2, "line 2"
    )
    assert is_valid is True


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_PY_DIR = ROOT_DIR / "sample_projects" / "vulnerable_python_app"


def test_deterministic_demo_review_mode():
    sample_dir = SAMPLE_PY_DIR
    contexts = [
        {
            "file_path": "auth.py",
            "content": "def update_user_profile(user_id: int, payload: dict):\n    result = db.connect().execute(payload)\n    return result\n",
            "total_lines": 3
        }
    ]

    findings = LLMReviewService.generate_deterministic_demo_review(sample_dir, contexts, [])
    assert len(findings) > 0
    for f in findings:
        assert f.is_demo is True
        assert f.is_ai_suggested is True
        assert "[Demo Mode]" in f.title
