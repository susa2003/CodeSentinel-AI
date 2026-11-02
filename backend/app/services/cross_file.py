import ast
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

from app.analyzers.base import BaseAnalyzer, AnalyzerResult, NormalizedFinding
from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum


class ModuleSymbolInfo:
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classes: Set[str] = set()
        self.functions: Set[str] = set()
        self.variables: Set[str] = set()
        # Imports: (imported_module_name, imported_symbol_name, line_number)
        self.imports: List[Tuple[str, Optional[str], int]] = []
        # Function calls made in this module: (called_name, line_number)
        self.calls: List[Tuple[str, int]] = []


class PythonModuleParser(ast.NodeVisitor):
    def __init__(self, info: ModuleSymbolInfo):
        self.info = info

    def visit_ClassDef(self, node: ast.ClassDef):
        self.info.classes.add(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.info.functions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.info.functions.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.info.variables.add(target.id)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.info.imports.append((alias.name, None, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.info.imports.append((mod, alias.name, node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.info.calls.append((node.func.id, node.lineno))
        elif isinstance(node.func, ast.Attribute):
            self.info.calls.append((node.func.attr, node.lineno))
        self.generic_visit(node)


class CrossFileAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "cross_file"

    @property
    def supported_languages(self) -> List[str]:
        return ["Python", "JavaScript", "TypeScript"]

    def is_available(self) -> bool:
        return True

    def _normalize_python_module_to_path(self, current_file: str, mod_name: str, all_files: Set[str]) -> Optional[str]:
        """Maps an import module name to an actual relative file path in the project."""
        # e.g. "utils.helpers" -> "utils/helpers.py" or "helpers.py"
        as_path = mod_name.replace(".", "/") + ".py"
        if as_path in all_files:
            return as_path

        # check in same directory as current file
        curr_dir = str(Path(current_file).parent).replace("\\", "/")
        if curr_dir and curr_dir != ".":
            nested = f"{curr_dir}/{as_path}"
            if nested in all_files:
                return nested

        # check as package __init__.py
        as_init = mod_name.replace(".", "/") + "/__init__.py"
        if as_init in all_files:
            return as_init

        # simple basename match
        parts = mod_name.split(".")
        base_match = f"{parts[-1]}.py"
        for f in all_files:
            if f.endswith(f"/{base_match}") or f == base_match:
                return f

        return None

    def _find_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Finds circular dependencies in module import graph."""
        cycles = []
        visited = set()
        stack = []

        def dfs(node: str):
            visited.add(node)
            stack.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in stack:
                    # Cycle found
                    idx = stack.index(neighbor)
                    cycle = stack[idx:] + [neighbor]
                    if len(cycle) > 2:
                        cycles.append(cycle)

            stack.pop()

        for n in list(graph.keys()):
            if n not in visited:
                dfs(n)

        # Deduplicate cycles
        unique_cycles = []
        seen = set()
        for c in cycles:
            norm_cycle = tuple(sorted(c[:-1]))
            if norm_cycle not in seen:
                seen.add(norm_cycle)
                unique_cycles.append(c)

        return unique_cycles

    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        start_time = time.time()
        findings: List[NormalizedFinding] = []

        modules: Dict[str, ModuleSymbolInfo] = {}
        all_relative_files = {item["relative_path"] for item in manifest_items}
        test_files = {item["relative_path"] for item in manifest_items if item.get("is_test_file")}
        source_files = all_relative_files - test_files

        # 1. Parse Python modules
        for item in manifest_items:
            rel_path = item["relative_path"]
            if item.get("language") == "Python":
                file_path = project_dir / rel_path
                info = ModuleSymbolInfo(rel_path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        tree = ast.parse(f.read(), filename=rel_path)
                    visitor = PythonModuleParser(info)
                    visitor.visit(tree)
                    modules[rel_path] = info
                except Exception:
                    continue
            elif item.get("language") in ("JavaScript", "TypeScript"):
                # Basic regex extraction for JS/TS
                file_path = project_dir / rel_path
                info = ModuleSymbolInfo(rel_path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    # Imports
                    import_matches = re.finditer(r'(?:import|from)\s+["\']([^"\']+)["\']', content)
                    for m in import_matches:
                        info.imports.append((m.group(1), None, 1))
                    # Functions
                    func_matches = re.findall(r'function\s+([a-zA-Z0-9_$]+)', content)
                    info.functions.update(func_matches)
                    modules[rel_path] = info
                except Exception:
                    continue

        # 2. Build Dependency Graph
        import_graph: Dict[str, Set[str]] = {rel: set() for rel in modules}
        for rel_path, info in modules.items():
            for mod_name, symbol_name, line in info.imports:
                target_file = self._normalize_python_module_to_path(rel_path, mod_name, all_relative_files)
                if target_file and target_file in modules:
                    import_graph[rel_path].add(target_file)

                    # 3. Check for Broken / Non-Existent Imported Symbols in target module
                    if symbol_name and symbol_name != "*":
                        target_info = modules[target_file]
                        known_symbols = target_info.functions | target_info.classes | target_info.variables
                        if known_symbols and symbol_name not in known_symbols:
                            findings.append(NormalizedFinding(
                                rule_id="CROSS-001",
                                source_analyzer=self.name,
                                file_path=rel_path,
                                start_line=line,
                                end_line=line,
                                severity=SeverityEnum.HIGH,
                                confidence=ConfidenceEnum.HIGH,
                                category=CategoryEnum.CROSS_FILE,
                                title=f"Imported symbol '{symbol_name}' not found in '{target_file}'",
                                explanation=(
                                    f"Module '{rel_path}' attempts to import '{symbol_name}' from '{target_file}', "
                                    f"but '{symbol_name}' is not defined as an exported function, class, or variable."
                                ),
                                evidence=f"from {mod_name} import {symbol_name}",
                                remediation=f"Verify symbol name in '{target_file}' or export '{symbol_name}'.",
                                doc_url="https://docs.python.org/3/reference/simple_stmts.html#the-import-statement"
                            ))

        # 4. Check for Circular Dependencies
        cycles = self._find_cycles(import_graph)
        for cycle in cycles:
            cycle_str = " -> ".join(cycle)
            findings.append(NormalizedFinding(
                rule_id="CROSS-002",
                source_analyzer=self.name,
                file_path=cycle[0],
                start_line=1,
                end_line=1,
                severity=SeverityEnum.MEDIUM,
                confidence=ConfidenceEnum.HIGH,
                category=CategoryEnum.CROSS_FILE,
                title="Circular dependency detected",
                explanation=f"A circular import cycle was detected among modules: {cycle_str}.",
                evidence=cycle_str,
                remediation="Refactor shared abstractions into a common utility module to eliminate circular imports.",
                doc_url="https://docs.python.org/3/tutorial/modules.html"
            ))

        # 5. Check for Untested Business Logic (source files with complex logic not touched by any tests)
        for src in source_files:
            if src in modules and len(modules[src].functions) >= 2:
                # check if any test file imports this module
                tested = False
                for t in test_files:
                    if src in import_graph.get(t, set()):
                        tested = True
                        break
                if not tested and test_files:
                    findings.append(NormalizedFinding(
                        rule_id="CROSS-003",
                        source_analyzer=self.name,
                        file_path=src,
                        start_line=1,
                        end_line=1,
                        severity=SeverityEnum.LOW,
                        confidence=ConfidenceEnum.MEDIUM,
                        category=CategoryEnum.TESTING,
                        title=f"Module '{src}' has no direct automated tests",
                        explanation=(
                            f"Module '{src}' contains {len(modules[src].functions)} function definitions "
                            "but is not imported or exercised by any detected test suites."
                        ),
                        evidence=None,
                        remediation=f"Add unit tests covering functions in '{src}'.",
                        doc_url="https://martinfowler.com/articles/practical-test-pyramid.html"
                    ))

        duration = round(time.time() - start_time, 3)
        return AnalyzerResult(
            analyzer_name=self.name,
            status="SUCCESS",
            duration_seconds=duration,
            findings=findings,
            message=f"Cross-file relationship graph analyzed {len(modules)} modules and found {len(findings)} structural issues."
        )


def select_targeted_context_for_llm(
    project_dir: Path,
    manifest_items: List[Dict[str, Any]],
    findings: List[NormalizedFinding],
    max_tokens: int = 6000
) -> List[Dict[str, Any]]:
    """
    Selects targeted code snippets based on high-risk findings and entry points.
    Limits tokens to prevent overwhelming the context window.
    """
    selected_files = set()
    
    # 1. Prioritize files with Critical or High severity findings
    for f in findings:
        if f.severity in (SeverityEnum.CRITICAL, SeverityEnum.HIGH):
            selected_files.add(f.file_path)

    # 2. Add entry points if space allows
    for item in manifest_items:
        if item.get("is_entry_point") and len(selected_files) < 4:
            selected_files.add(item["relative_path"])

    # 3. Fallback to first few source files if no high severity findings
    if not selected_files:
        for item in manifest_items:
            if not item.get("is_test_file") and item.get("language") in ("Python", "JavaScript", "TypeScript"):
                selected_files.add(item["relative_path"])
                if len(selected_files) >= 3:
                    break

    contexts = []
    char_budget = max_tokens * 4  # rough token approximation: 1 token ~= 4 chars

    for rel_path in selected_files:
        file_path = project_dir / rel_path
        if not file_path.exists():
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # truncate content if exceeding single file budget
            truncated = content[:2500]
            if len(content) > 2500:
                truncated += "\n... [Remaining content truncated for targeted analysis] ..."

            contexts.append({
                "file_path": rel_path,
                "content": truncated,
                "total_lines": len(content.splitlines()),
                "findings_here": [
                    {"rule_id": f.rule_id, "title": f.title, "line": f.start_line, "severity": f.severity.value}
                    for f in findings if f.file_path == rel_path
                ]
            })

            char_budget -= len(truncated)
            if char_budget <= 0:
                break
        except Exception:
            continue

    return contexts
