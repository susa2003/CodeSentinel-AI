import re
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.analyzers.base import BaseAnalyzer, AnalyzerResult, NormalizedFinding
from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum, VerificationStatusEnum
from app.core.security import redact_secrets


# Pattern definitions: (regex, rule_id, severity, confidence, category, title, explanation, remediation, languages)
PATTERN_RULES = [
    (
        r'\b(?:eval|new\s+Function)\s*\(',
        "JS-SEC-001",
        SeverityEnum.CRITICAL,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Dynamic code evaluation with eval() or Function()",
        "Dynamic code evaluation allows execution of arbitrary strings as code, leading to severe Cross-Site Scripting (XSS) or Remote Code Execution (RCE).",
        "Avoid dynamic evaluation. Use typed JSON parsing (JSON.parse) or well-defined dispatch maps.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'\.(?:innerHTML|outerHTML)\s*=',
        "JS-SEC-002",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Direct assignment to innerHTML/outerHTML (DOM XSS)",
        "Assigning unsanitized data directly to innerHTML bypasses HTML encoding and permits attackers to inject malicious script tags into the DOM.",
        "Use textContent, innerText, or a sanitization library such as DOMPurify before rendering.",
        {"JavaScript", "TypeScript", "HTML"}
    ),
    (
        r'document\.write\s*\(',
        "JS-SEC-003",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Use of document.write()",
        "document.write() is an obsolete and dangerous method that can overwrite the page or execute injected scripts.",
        "Use modern DOM manipulation methods such as document.createElement and appendChild.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:',
        "JS-SEC-004",
        SeverityEnum.MEDIUM,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Usage of dangerouslySetInnerHTML in React",
        "dangerouslySetInnerHTML bypasses React's built-in XSS protection. If the input contains unescaped user data, it can cause XSS.",
        "Sanitize HTML content using DOMPurify before passing to __html, or render native React elements.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'(?:rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["\']?0["\']?)',
        "JS-SEC-005",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "TLS / SSL certificate verification disabled",
        "Disabling TLS certificate verification leaves network connections vulnerable to Man-in-the-Middle (MITM) attacks.",
        "Always enforce valid SSL/TLS certificates in production environments.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'\.__proto__\s*=',
        "JS-SEC-006",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Potential Prototype Pollution via __proto__ assignment",
        "Modifying __proto__ can pollute the global Object prototype, altering the behavior of all objects and potentially enabling code execution.",
        "Use Object.create(null) for maps or use Map data structures.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'(?:query|execute)\s*\(\s*`[^`]*\$\{[^}]+\}[^`]*`',
        "DB-SEC-001",
        SeverityEnum.CRITICAL,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "SQL injection risk with template literal interpolation",
        "Interpolating variables directly into a SQL template literal bypasses query parameterization and allows SQL injection.",
        "Use parameterized query bindings: query('SELECT * FROM users WHERE id = $1', [userId]).",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'(?i)Runtime\.getRuntime\(\)\.exec\(',
        "JAVA-SEC-001",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "System command execution with Runtime.getRuntime().exec()",
        "Directly executing system commands in Java may allow command injection if arguments are unvalidated.",
        "Use ProcessBuilder with explicit arguments and strict validation.",
        {"Java"}
    ),
    (
        r'(?i)Cipher\.getInstance\s*\(\s*["\'](?:DES|RC4)["\']\)',
        "JAVA-SEC-002",
        SeverityEnum.HIGH,
        ConfidenceEnum.HIGH,
        CategoryEnum.SECURITY,
        "Weak cryptographic cipher (DES / RC4)",
        "DES and RC4 are cryptographically broken algorithms susceptible to known cryptanalysis attacks.",
        "Use AES/GCM/NoPadding with at least 256-bit keys.",
        {"Java"}
    ),
    (
        r'\b(?:localStorage|sessionStorage)\.setItem\s*\(\s*["\'](?:token|auth_token|jwt|accessToken)["\']',
        "JS-SEC-007",
        SeverityEnum.LOW,
        ConfidenceEnum.MEDIUM,
        CategoryEnum.SECURITY,
        "Authentication token stored in web storage",
        "Storing sensitive auth tokens in localStorage or sessionStorage exposes them to theft via Cross-Site Scripting (XSS).",
        "Use HttpOnly, Secure, SameSite cookies for storing sensitive session tokens.",
        {"JavaScript", "TypeScript"}
    ),
    (
        r'(?i)console\.log\s*\(\s*.*(?:password|secret|apiKey|api_key|token).*',
        "GEN-SEC-001",
        SeverityEnum.MEDIUM,
        ConfidenceEnum.MEDIUM,
        CategoryEnum.SECURITY,
        "Logging potential credentials or sensitive variables",
        "Writing sensitive tokens or credentials to the console or logs can expose them to unauthorized log aggregation services.",
        "Remove console logging of sensitive authentication variables.",
        {"JavaScript", "TypeScript", "Python"}
    ),
]


class PatternEngineAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "pattern_engine"

    @property
    def supported_languages(self) -> List[str]:
        return ["JavaScript", "TypeScript", "Java", "HTML", "CSS", "Python"]

    def is_available(self) -> bool:
        return True

    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        start_time = time.time()
        findings: List[NormalizedFinding] = []

        # Compile rules
        compiled_rules = [
            (re.compile(pattern), rule_id, sev, conf, cat, title, expl, remed, langs)
            for pattern, rule_id, sev, conf, cat, title, expl, remed, langs in PATTERN_RULES
        ]

        eligible_items = [
            item for item in manifest_items
            if item.get("language") in self.supported_languages
        ]

        for item in eligible_items:
            rel_path = item["relative_path"]
            file_path = project_dir / rel_path
            file_lang = item.get("language")

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                lines = content.splitlines()

                for line_idx, line in enumerate(lines, start=1):
                    stripped_line = line.strip()
                    if not stripped_line or stripped_line.startswith(("//", "/*", "*", "#")):
                        continue

                    for regex, rule_id, sev, conf, cat, title, expl, remed, langs in compiled_rules:
                        if file_lang in langs and regex.search(line):
                            evidence = redact_secrets(stripped_line)
                            findings.append(NormalizedFinding(
                                rule_id=rule_id,
                                source_analyzer=self.name,
                                file_path=rel_path,
                                start_line=line_idx,
                                end_line=line_idx,
                                severity=sev,
                                confidence=conf,
                                category=cat,
                                title=title,
                                explanation=expl,
                                evidence=evidence,
                                remediation=remed,
                                doc_url="https://owasp.org/www-project-top-ten/"
                            ))
            except Exception:
                continue

        duration = time.time() - start_time
        return AnalyzerResult(
            analyzer_name=self.name,
            status="SUCCESS",
            duration_seconds=round(duration, 3),
            findings=findings,
            message=f"Analyzed {len(eligible_items)} source files with polyglot pattern rules."
        )
