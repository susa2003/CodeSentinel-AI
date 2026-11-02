import ast
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.analyzers.base import BaseAnalyzer, AnalyzerResult, NormalizedFinding
from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum, VerificationStatusEnum
from app.core.security import redact_secrets


class ASTVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, source_code: str, is_test: bool):
        self.rel_path = rel_path
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.is_test = is_test
        self.findings: List[NormalizedFinding] = []

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Mutable Default Arguments
        defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
        for d in defaults:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                evidence = self._get_line_snippet(node.lineno)
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-001",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.HIGH,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.BUG_RISK,
                    title=f"Mutable default argument in '{node.name}'",
                    explanation=(
                        f"Function '{node.name}' defines a mutable default argument (list, dict, or set). "
                        "Python creates default arguments once when the function is defined, causing state to persist "
                        "across separate function calls."
                    ),
                    evidence=evidence,
                    remediation="Use `None` as default and initialize the mutable object inside the function body: `arg = arg if arg is not None else []`.",
                    doc_url="https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments"
                ))

        # Check for first argument 'self' in class methods if inside class (handled if tracked)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Detect SQL query constructed with concatenation
        if isinstance(node.value, (ast.BinOp, ast.JoinedStr)):
            line_str = self._get_line_snippet(node.lineno).upper()
            if any(sql_kw in line_str for sql_kw in ("SELECT ", "INSERT INTO ", "UPDATE ", "DELETE FROM ")):
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-009",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.CRITICAL,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.SECURITY,
                    title="Potential SQL Injection via dynamically constructed query string",
                    explanation="SQL query constructed via string formatting or concatenation. Untrusted input will compromise the database.",
                    evidence=self._get_line_snippet(node.lineno),
                    remediation="Use parameterized queries with placeholder bindings instead of string interpolation.",
                    doc_url="https://owasp.org/www-community/attacks/SQL_Injection"
                ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
        for d in defaults:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-001",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.HIGH,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.BUG_RISK,
                    title=f"Mutable default argument in async '{node.name}'",
                    explanation=f"Async function '{node.name}' defines a mutable default argument.",
                    evidence=self._get_line_snippet(node.lineno),
                    remediation="Use `None` as default parameter value and initialize inside the function.",
                    doc_url="https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments"
                ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # 2. Bare except or catching BaseException
        if node.type is None:
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-002",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.MEDIUM,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.QUALITY,
                title="Bare 'except:' clause catches all exceptions",
                explanation=(
                    "A bare 'except:' clause catches all exceptions, including `KeyboardInterrupt` and `SystemExit`. "
                    "This masks unintended programming bugs and prevents graceful process shutdowns."
                ),
                evidence=self._get_line_snippet(node.lineno),
                remediation="Catch specific exception classes (e.g., `except (ValueError, KeyError) as e:`) or at least `except Exception:`.",
                doc_url="https://peps.python.org/pep-0008/#programming-recommendations"
            ))
        elif isinstance(node.type, ast.Name) and node.type.id == "BaseException":
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-003",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.MEDIUM,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.QUALITY,
                title="Catching BaseException directly",
                explanation="Catching `BaseException` intercepts system exits, keyboard interrupts, and generator exits.",
                evidence=self._get_line_snippet(node.lineno),
                remediation="Catch `Exception` instead of `BaseException` unless writing a root-level crash handler.",
                doc_url="https://docs.python.org/3/library/exceptions.html#exception-hierarchy"
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 3. Dangerous eval/exec
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-004",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.CRITICAL,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.SECURITY,
                title=f"Dangerous dynamic code execution with '{func_name}'",
                explanation=(
                    f"Use of '{func_name}' allows execution of arbitrary code. If any part of the input originates from "
                    "external sources, this leads to Remote Code Execution (RCE) vulnerabilities."
                ),
                evidence=self._get_line_snippet(node.lineno),
                remediation="Use `ast.literal_eval` for parsing safe Python literals, or use JSON/YAML serializers.",
                doc_url="https://owasp.org/www-community/attacks/Code_Injection"
            ))

        # 4. os.system or subprocess shell=True
        if func_name == "system" and isinstance(getattr(node.func, "value", None), ast.Name) and node.func.value.id == "os":
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-005",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.HIGH,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.SECURITY,
                title="Use of insecure 'os.system' for command execution",
                explanation="`os.system` executes commands in a subshell, exposing the application to shell injection attacks.",
                evidence=self._get_line_snippet(node.lineno),
                remediation="Use `subprocess.run([...], check=True, shell=False)` with arguments passed as an explicit list.",
                doc_url="https://docs.python.org/3/library/subprocess.html#security-considerations"
            ))

        if func_name in ("run", "Popen", "call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append(NormalizedFinding(
                        rule_id="PY-AST-006",
                        source_analyzer="python_ast",
                        file_path=self.rel_path,
                        start_line=node.lineno,
                        end_line=node.lineno,
                        severity=SeverityEnum.HIGH,
                        confidence=ConfidenceEnum.HIGH,
                        category=CategoryEnum.SECURITY,
                        title="Subprocess invoked with shell=True",
                        explanation="Spawning a process with `shell=True` allows shell metacharacters in arguments to execute unintended commands.",
                        evidence=self._get_line_snippet(node.lineno),
                        remediation="Set `shell=False` and pass arguments as a list of strings: `subprocess.run(['cmd', arg1, arg2])`.",
                        doc_url="https://docs.python.org/3/library/subprocess.html#security-considerations"
                    ))

        # 5. Insecure tempfile.mktemp
        if func_name == "mktemp":
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-007",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.HIGH,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.SECURITY,
                title="Insecure temporary file creation with 'tempfile.mktemp'",
                explanation="`tempfile.mktemp` creates a race condition vulnerability (TOCTOU) allowing attackers to intercept or hijack the file path.",
                evidence=self._get_line_snippet(node.lineno),
                remediation="Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()` instead.",
                doc_url="https://docs.python.org/3/library/tempfile.html#tempfile.mktemp"
            ))

        # 6. Weak cryptographic hashing (MD5, SHA1)
        if func_name in ("md5", "sha1"):
            usedforsec = False
            for kw in node.keywords:
                if kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    usedforsec = True
            if not usedforsec and not self.is_test:
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-008",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.MEDIUM,
                    confidence=ConfidenceEnum.MEDIUM,
                    category=CategoryEnum.SECURITY,
                    title=f"Weak hash algorithm 'hashlib.{func_name}'",
                    explanation=f"MD5 and SHA-1 have known collision vulnerabilities and should not be used for security purposes.",
                    evidence=self._get_line_snippet(node.lineno),
                    remediation="Use `hashlib.sha256()` or `hashlib.sha512()`, or pass `usedforsecurity=False` if used for non-security checksums.",
                    doc_url="https://owasp.org/www-community/vulnerabilities/Insecure_Cryptographic_Storage"
                ))

        # 7. SQL Injection in cursor.execute with string concatenation or format
        if func_name in ("execute", "executemany"):
            if node.args and isinstance(node.args[0], (ast.BinOp, ast.JoinedStr)):
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-009",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.CRITICAL,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.SECURITY,
                    title="Potential SQL Injection via dynamically constructed query",
                    explanation="SQL query appears to be constructed using string formatting or concatenation rather than parameterized queries.",
                    evidence=self._get_line_snippet(node.lineno),
                    remediation="Use parameterized queries: `cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))`.",
                    doc_url="https://owasp.org/www-community/attacks/SQL_Injection"
                ))

        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        # 8. Assert used in production code
        if not self.is_test:
            evidence = self._get_line_snippet(node.lineno)
            self.findings.append(NormalizedFinding(
                rule_id="PY-AST-010",
                source_analyzer="python_ast",
                file_path=self.rel_path,
                start_line=node.lineno,
                end_line=node.lineno,
                severity=SeverityEnum.LOW,
                confidence=ConfidenceEnum.MEDIUM,
                category=CategoryEnum.BUG_RISK,
                title="Assert statement used outside of test code",
                explanation=(
                    "Assert statements are removed when Python is executed with optimization flags (-O or -OO). "
                    "Do not rely on assert for business logic or security permission checks."
                ),
                evidence=evidence,
                remediation="Raise explicit exceptions such as `if not condition: raise ValueError(...)`.",
                doc_url="https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement"
            ))
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # 9. Division by zero in literal expression
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.findings.append(NormalizedFinding(
                    rule_id="PY-AST-011",
                    source_analyzer="python_ast",
                    file_path=self.rel_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    severity=SeverityEnum.HIGH,
                    confidence=ConfidenceEnum.HIGH,
                    category=CategoryEnum.BUG_RISK,
                    title="Literal division by zero detected",
                    explanation="Operation divides by constant zero, which will immediately raise a `ZeroDivisionError` at runtime.",
                    evidence=self._get_line_snippet(node.lineno),
                    remediation="Ensure the denominator is validated and non-zero.",
                    doc_url="https://docs.python.org/3/library/exceptions.html#ZeroDivisionError"
                ))
        self.generic_visit(node)


class PythonASTAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "python_ast"

    @property
    def supported_languages(self) -> List[str]:
        return ["Python"]

    def is_available(self) -> bool:
        return True  # Built-in Python standard library AST

    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        start_time = time.time()
        findings: List[NormalizedFinding] = []

        if "Python" not in detected_languages:
            return AnalyzerResult(
                analyzer_name=self.name,
                status="SKIPPED",
                duration_seconds=0.0,
                skip_reason="No Python files detected in the project."
            )

        python_files = [
            item for item in manifest_items
            if item.get("language") == "Python"
        ]

        for item in python_files:
            rel_path = item["relative_path"]
            file_path = project_dir / rel_path
            is_test = item.get("is_test_file", False)

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                try:
                    tree = ast.parse(content, filename=rel_path)
                    visitor = ASTVisitor(rel_path, content, is_test)
                    visitor.visit(tree)
                    findings.extend(visitor.findings)
                except SyntaxError as e:
                    line_snippet = e.text.strip() if e.text else ""
                    findings.append(NormalizedFinding(
                        rule_id="PY-SYNTAX-001",
                        source_analyzer=self.name,
                        file_path=rel_path,
                        start_line=e.lineno or 1,
                        end_line=e.lineno or 1,
                        severity=SeverityEnum.CRITICAL,
                        confidence=ConfidenceEnum.HIGH,
                        category=CategoryEnum.SYNTAX,
                        title=f"Syntax Error: {e.msg}",
                        explanation=f"Python parser failed to parse file due to syntax error: {e.msg}",
                        evidence=line_snippet,
                        remediation="Fix the invalid Python syntax at the indicated line number.",
                        doc_url="https://docs.python.org/3/library/exceptions.html#SyntaxError"
                    ))
            except Exception:
                continue

        duration = time.time() - start_time
        return AnalyzerResult(
            analyzer_name=self.name,
            status="SUCCESS",
            duration_seconds=round(duration, 3),
            findings=findings,
            message=f"Scanned {len(python_files)} Python files via AST engine."
        )
