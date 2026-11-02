import os
import re
from pathlib import Path
from typing import Tuple, List, Optional

# Secret detection patterns (regexes)
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{12,})["\']?', "API / Auth Key"),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{6,})["\']?', "Hardcoded Password"),
    (r'(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})', "Bearer Token"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?', "AWS Secret Key"),
    (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', "Private Key Block"),
    (r'sk-(?:proj-|live-)?[a-zA-Z0-9_\-]{20,}', "OpenAI API Key"),
    (r'gh[pousr]_[a-zA-Z0-9]{20,}', "GitHub Personal Access Token"),
    (r'glpat-[a-zA-Z0-9_\-]{20,}', "GitLab Personal Access Token"),
    (r'xox[baprs]-[0-9a-zA-Z]{10,48}', "Slack Token"),
]

COMPILED_SECRET_PATTERNS = [(re.compile(pat), desc) for pat, desc in SECRET_PATTERNS]


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """
    Ensure target_path resolves strictly within base_dir without escaping.
    Prevents directory traversal (ZipSlip, '..', absolute path injection).
    """
    try:
        base_dir_resolved = base_dir.resolve()
        target_path_resolved = target_path.resolve()
        
        # Check if target is relative to base
        target_path_resolved.relative_to(base_dir_resolved)
        return True
    except (ValueError, RuntimeError):
        return False


def validate_archive_entry_name(entry_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a zip entry name before extraction.
    Rejects path traversals, drive letters, leading slashes, null bytes, and suspicious characters.
    """
    if not entry_name:
        return False, "Empty archive entry name"
        
    if "\0" in entry_name:
        return False, "Null byte in archive entry name"

    # Normalize backslashes to forward slashes for checking
    normalized = entry_name.replace("\\", "/")
    
    # Reject absolute paths (Unix or Windows drive letters)
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        return False, f"Absolute path traversal detected: {entry_name}"

    # Split components and check for traversal
    parts = normalized.split("/")
    for part in parts:
        if part == "..":
            return False, f"Directory traversal '..' detected in path: {entry_name}"

    return True, None


def redact_secrets(text: str) -> str:
    """
    Redacts sensitive credentials, tokens, and passwords from source snippets and logs.
    """
    if not text:
        return text
        
    redacted = text
    for pattern, _ in COMPILED_SECRET_PATTERNS:
        # If it's key=value pattern with groups, mask group 2
        def replace_match(match):
            full_match = match.group(0)
            if len(match.groups()) >= 2:
                prefix = match.group(1)
                secret_val = match.group(2)
                return full_match.replace(secret_val, f"***REDACTED_{len(secret_val)}_CHARS***")
            elif len(match.groups()) == 1:
                secret_val = match.group(1)
                return full_match.replace(secret_val, f"***REDACTED_{len(secret_val)}_CHARS***")
            else:
                return "***REDACTED_SECRET***"

        redacted = pattern.sub(replace_match, redacted)

    return redacted


def detect_secrets_in_text(text: str, file_path: str) -> List[dict]:
    """
    Scans a source file string for credentials and returns findings with line numbers.
    """
    findings = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        for pattern, desc in COMPILED_SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                masked_line = redact_secrets(line)
                findings.append({
                    "type": "hardcoded_secret",
                    "description": desc,
                    "line": line_idx,
                    "file_path": file_path,
                    "masked_evidence": masked_line.strip()
                })
                break  # avoid multiple hits on the same line
    return findings
