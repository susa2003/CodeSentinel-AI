import os
import sys
import json
import time
import shutil
import asyncio
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.analyzers.base import BaseAnalyzer, AnalyzerResult, NormalizedFinding
from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum
from app.core.config import settings
from app.core.security import redact_secrets


def map_ruff_code_to_meta(code: str) -> tuple[SeverityEnum, CategoryEnum]:
    """Maps Ruff rule codes to Severity and Category."""
    if not code:
        return SeverityEnum.MEDIUM, CategoryEnum.QUALITY

    if code.startswith("S"):  # flake8-bandit (Security)
        return SeverityEnum.HIGH, CategoryEnum.SECURITY
    elif code.startswith("F821") or code.startswith("F822") or code.startswith("F823"):  # undefined name
        return SeverityEnum.HIGH, CategoryEnum.BUG_RISK
    elif code.startswith("F"):  # general pyflakes
        return SeverityEnum.MEDIUM, CategoryEnum.BUG_RISK
    elif code.startswith("B"):  # flake8-bugbear
        return SeverityEnum.MEDIUM, CategoryEnum.BUG_RISK
    elif code.startswith("PERF"):  # perflint
        return SeverityEnum.LOW, CategoryEnum.PERFORMANCE
    elif code.startswith("C90") or code.startswith("PLR"):  # complexity
        return SeverityEnum.MEDIUM, CategoryEnum.MAINTAINABILITY
    elif code.startswith("PT"):  # pytest-style
        return SeverityEnum.LOW, CategoryEnum.TESTING
    elif code.startswith("E") or code.startswith("W"):
        return SeverityEnum.LOW, CategoryEnum.QUALITY
    else:
        return SeverityEnum.LOW, CategoryEnum.QUALITY


class RuffAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "ruff"

    @property
    def supported_languages(self) -> List[str]:
        return ["Python"]

    def is_available(self) -> bool:
        """Verifies if Ruff executable binary or python module is available."""
        if shutil.which("ruff"):
            return True
        try:
            return importlib.util.find_spec("ruff") is not None
        except Exception:
            return False

    def _get_command(self) -> Optional[List[str]]:
        """Resolves the executable command for Ruff."""
        ruff_exec = shutil.which("ruff")
        if ruff_exec:
            return [ruff_exec, "check", "--output-format=json", "--exit-zero", "."]

        try:
            if importlib.util.find_spec("ruff") is not None:
                return [sys.executable, "-m", "ruff", "check", "--output-format=json", "--exit-zero", "."]
        except Exception:
            pass

        return None

    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        start_time = time.time()

        if "Python" not in detected_languages:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="No Python files detected in the project."
            )

        if not settings.RUFF_ENABLED:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Ruff analyzer is disabled in settings."
            )

        if not self.is_available():
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Ruff executable or module is not installed."
            )

        cmd = self._get_command()
        if not cmd:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Ruff executable could not be resolved."
            )

        if not project_dir.exists() or not project_dir.is_dir():
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=0.0,
                message=f"Project directory does not exist or is not a directory: {project_dir}"
            )

        try:
            env = os.environ.copy()
            for k in list(env.keys()):
                if any(sec in k.lower() for sec in ["secret", "token", "password", "key"]):
                    env.pop(k, None)

            def _execute_subprocess():
                return subprocess.run(
                    cmd,
                    cwd=str(project_dir),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=settings.ANALYZER_TIMEOUT_SECONDS
                )

            # Use asyncio.to_thread for robust, cross-platform subprocess execution without Proactor loop requirement
            res = await asyncio.to_thread(_execute_subprocess)

            stdout_text = (res.stdout or "").strip()
            stderr_text = (res.stderr or "").strip()
            clean_stderr = redact_secrets(stderr_text)
            clean_stdout = redact_secrets(stdout_text)

            # Handle non-zero exit codes when no findings or fatal error
            if res.returncode != 0:
                if not stdout_text:
                    err_msg = clean_stderr or f"Process exited with code {res.returncode}"
                    return AnalyzerResult(
                        analyzer_name=self.name,
                        status="FAILED",
                        duration_seconds=round(time.time() - start_time, 3),
                        message=f"Ruff execution failed (exit code {res.returncode}): {err_msg}"
                    )

            if not stdout_text:
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="SUCCESS",
                    duration_seconds=round(time.time() - start_time, 3),
                    findings=[],
                    message="Ruff reported 0 issues."
                )

            try:
                data = json.loads(stdout_text)
            except json.JSONDecodeError as jde:
                err_detail = clean_stderr or clean_stdout[:200] or str(jde)
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message=f"Failed to parse Ruff JSON output: {err_detail}"
                )

            if not isinstance(data, list):
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message="Ruff output format unexpected: expected list of findings."
                )

            findings: List[NormalizedFinding] = []
            for item in data:
                code = item.get("code") or "RUFF-RULE"
                raw_file = item.get("filename", "")
                try:
                    rel_path = str(Path(raw_file).relative_to(project_dir)).replace("\\", "/")
                except ValueError:
                    rel_path = raw_file.replace("\\", "/")

                start_loc = item.get("location", {})
                end_loc = item.get("end_location", {})
                start_line = start_loc.get("row", 1)
                end_line = end_loc.get("row", start_line)

                sev, cat = map_ruff_code_to_meta(code)
                msg = item.get("message", "Lint warning")

                findings.append(NormalizedFinding(
                    rule_id=f"RUFF-{code}",
                    source_analyzer=self.name,
                    file_path=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    severity=sev,
                    confidence=ConfidenceEnum.HIGH,
                    category=cat,
                    title=f"[{code}] {msg}",
                    explanation=f"Ruff detected rule violation {code}: {msg}",
                    evidence=None,
                    remediation="Address the linting violation or apply suggested fix.",
                    doc_url=item.get("url") or f"https://docs.astral.sh/ruff/rules/{code.lower()}"
                ))

            duration = round(time.time() - start_time, 3)
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SUCCESS",
                duration_seconds=duration,
                findings=findings,
                message=f"Ruff scanned project and identified {len(findings)} findings."
            )

        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Ruff execution timed out after {settings.ANALYZER_TIMEOUT_SECONDS}s"
            )
        except FileNotFoundError as fnf:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Ruff executable not found: {fnf.filename or str(fnf) or 'executable missing'}"
            )
        except Exception as e:
            err_type = type(e).__name__
            err_str = str(e).strip()
            err_msg = f"{err_type}: {err_str}" if err_str else err_type
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Ruff execution error: {redact_secrets(err_msg)}"
            )
