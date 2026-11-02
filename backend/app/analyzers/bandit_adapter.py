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


def map_bandit_severity(sev_str: str, test_id: str) -> SeverityEnum:
    if test_id in ("B608", "B102", "B301", "B506"):  # Hardcore SQLi, exec, pickle, yaml
        return SeverityEnum.CRITICAL
    s = str(sev_str).upper()
    if s == "HIGH":
        return SeverityEnum.HIGH
    elif s == "MEDIUM":
        return SeverityEnum.MEDIUM
    elif s == "LOW":
        return SeverityEnum.LOW
    return SeverityEnum.INFORMATIONAL


def map_bandit_confidence(conf_str: str) -> ConfidenceEnum:
    c = str(conf_str).upper()
    if c == "HIGH":
        return ConfidenceEnum.HIGH
    elif c == "MEDIUM":
        return ConfidenceEnum.MEDIUM
    return ConfidenceEnum.LOW


class BanditAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "bandit"

    @property
    def supported_languages(self) -> List[str]:
        return ["Python"]

    def is_available(self) -> bool:
        """Verifies if Bandit executable binary or python module is available."""
        if shutil.which("bandit"):
            return True
        try:
            return importlib.util.find_spec("bandit") is not None
        except Exception:
            return False

    def _get_command(self) -> Optional[List[str]]:
        """Resolves the executable command for Bandit."""
        bandit_exec = shutil.which("bandit")
        if bandit_exec:
            return [bandit_exec, "-r", ".", "-f", "json", "-q", "--exit-zero"]

        try:
            if importlib.util.find_spec("bandit") is not None:
                return [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "-q", "--exit-zero"]
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

        if not settings.BANDIT_ENABLED:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Bandit security analyzer is disabled in settings."
            )

        if not self.is_available():
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Bandit executable or module is not installed."
            )

        cmd = self._get_command()
        if not cmd:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Bandit executable could not be resolved."
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

            # Use asyncio.to_thread for robust, cross-platform execution without Proactor loop requirement
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
                        message=f"Bandit execution failed (exit code {res.returncode}): {err_msg}"
                    )

            if not stdout_text:
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="SUCCESS",
                    duration_seconds=round(time.time() - start_time, 3),
                    findings=[],
                    message="Bandit reported 0 security vulnerabilities."
                )

            try:
                data = json.loads(stdout_text)
            except json.JSONDecodeError as jde:
                err_detail = clean_stderr or clean_stdout[:200] or str(jde)
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message=f"Failed to parse Bandit JSON output: {err_detail}"
                )

            if not isinstance(data, dict):
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message="Bandit output format unexpected: expected JSON object."
                )

            findings: List[NormalizedFinding] = []
            results = data.get("results", [])

            for item in results:
                test_id = item.get("test_id", "B000")
                test_name = item.get("test_name", "Security Issue")
                issue_text = item.get("issue_text", "")
                raw_file = item.get("filename", "")
                try:
                    rel_path = str(Path(raw_file).relative_to(project_dir)).replace("\\", "/")
                except ValueError:
                    rel_path = raw_file.replace("\\", "/")

                start_line = item.get("line_number", 1)
                line_range = item.get("line_range", [start_line])
                end_line = line_range[-1] if line_range else start_line

                sev = map_bandit_severity(item.get("issue_severity", "MEDIUM"), test_id)
                conf = map_bandit_confidence(item.get("issue_confidence", "MEDIUM"))
                code_snippet = redact_secrets(item.get("code", "").strip())

                findings.append(NormalizedFinding(
                    rule_id=f"BANDIT-{test_id}",
                    source_analyzer=self.name,
                    file_path=rel_path,
                    start_line=start_line,
                    end_line=end_line,
                    severity=sev,
                    confidence=conf,
                    category=CategoryEnum.SECURITY,
                    title=f"[{test_id}] {test_name}: {issue_text}",
                    explanation=f"Bandit identified security flaw '{test_name}' (CWE-{item.get('issue_cwe', {}).get('id', 'N/A')}): {issue_text}",
                    evidence=code_snippet,
                    remediation="Consult Bandit documentation and remediate the flagged vulnerability.",
                    doc_url=item.get("more_info") or f"https://bandit.readthedocs.io/en/latest/plugins/{test_id.lower()}_{test_name}.html"
                ))

            duration = round(time.time() - start_time, 3)
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SUCCESS",
                duration_seconds=duration,
                findings=findings,
                message=f"Bandit security scan completed with {len(findings)} findings."
            )

        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Bandit execution timed out after {settings.ANALYZER_TIMEOUT_SECONDS}s"
            )
        except FileNotFoundError as fnf:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Bandit executable not found: {fnf.filename or str(fnf) or 'executable missing'}"
            )
        except Exception as e:
            err_type = type(e).__name__
            err_str = str(e).strip()
            err_msg = f"{err_type}: {err_str}" if err_str else err_type
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Bandit execution error: {redact_secrets(err_msg)}"
            )
