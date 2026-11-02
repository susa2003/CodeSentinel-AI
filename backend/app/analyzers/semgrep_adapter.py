import os
import sys
import json
import time
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.analyzers.base import BaseAnalyzer, AnalyzerResult, NormalizedFinding
from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum
from app.core.config import settings
from app.core.security import redact_secrets


class SemgrepAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "semgrep"

    @property
    def supported_languages(self) -> List[str]:
        return ["Python", "JavaScript", "TypeScript", "Java", "Go", "C", "C++"]

    def is_available(self) -> bool:
        return shutil.which("semgrep") is not None

    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        start_time = time.time()

        if not self.is_available():
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Semgrep CLI binary is not installed in the host system. Skipped gracefully."
            )

        if not settings.SEMGREP_ENABLED:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="Semgrep analyzer is disabled in settings."
            )

        if not project_dir.exists() or not project_dir.is_dir():
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=0.0,
                message=f"Project directory does not exist or is not a directory: {project_dir}"
            )

        cmd = ["semgrep", "scan", "--json", "--quiet", "--config=auto"]

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

            res = await asyncio.to_thread(_execute_subprocess)

            stdout_text = (res.stdout or "").strip()
            stderr_text = (res.stderr or "").strip()
            clean_stderr = redact_secrets(stderr_text)
            clean_stdout = redact_secrets(stdout_text)

            if res.returncode != 0 and not stdout_text:
                err_msg = clean_stderr or f"Process exited with code {res.returncode}"
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message=f"Semgrep execution failed (exit code {res.returncode}): {err_msg}"
                )

            if not stdout_text:
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="SUCCESS",
                    duration_seconds=round(time.time() - start_time, 3),
                    findings=[]
                )

            try:
                data = json.loads(stdout_text)
            except json.JSONDecodeError as jde:
                err_detail = clean_stderr or clean_stdout[:200] or str(jde)
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status="FAILED",
                    duration_seconds=round(time.time() - start_time, 3),
                    message=f"Failed to parse Semgrep JSON output: {err_detail}"
                )

            findings: List[NormalizedFinding] = []
            for item in data.get("results", []):
                rule_id = item.get("check_id", "SEMGREP")
                raw_path = item.get("path", "")
                try:
                    rel_path = str(Path(raw_path).relative_to(project_dir)).replace("\\", "/")
                except ValueError:
                    rel_path = raw_path.replace("\\", "/")

                start = item.get("start", {}).get("line", 1)
                end = item.get("end", {}).get("line", start)
                extra = item.get("extra", {})
                msg = extra.get("message", "Semgrep security finding")
                sev_raw = extra.get("severity", "WARNING").upper()

                sev = SeverityEnum.MEDIUM
                if sev_raw in ("ERROR", "CRITICAL"):
                    sev = SeverityEnum.HIGH
                elif sev_raw == "INFO":
                    sev = SeverityEnum.LOW

                evidence_line = redact_secrets(extra.get("lines", "").strip())

                findings.append(NormalizedFinding(
                    rule_id=f"SEMGREP-{rule_id}",
                    source_analyzer=self.name,
                    file_path=rel_path,
                    start_line=start,
                    end_line=end,
                    severity=sev,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.SECURITY,
                    title=f"[{rule_id}] {msg[:80]}",
                    explanation=msg,
                    evidence=evidence_line,
                    remediation="Follow Semgrep rule recommendation to address the issue."
                ))

            return AnalyzerResult(
                analyzer_name=self.name,
                status="SUCCESS",
                duration_seconds=round(time.time() - start_time, 3),
                findings=findings
            )

        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Semgrep execution timed out after {settings.ANALYZER_TIMEOUT_SECONDS}s"
            )
        except FileNotFoundError as fnf:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Semgrep executable not found: {fnf.filename or str(fnf) or 'executable missing'}"
            )
        except Exception as e:
            err_type = type(e).__name__
            err_str = str(e).strip()
            err_msg = f"{err_type}: {err_str}" if err_str else err_type
            return AnalyzerResult(
                analyzer_name=self.name,
                status="FAILED",
                duration_seconds=round(time.time() - start_time, 3),
                message=f"Semgrep execution error: {redact_secrets(err_msg)}"
            )
