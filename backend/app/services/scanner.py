import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.core.config import settings
from app.core.security import detect_secrets_in_text

# Mapping file extensions to language names
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".java": "Java",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
}

ENTRY_POINT_FILENAMES = {
    "main.py", "app.py", "wsgi.py", "asgi.py", "server.py", "__main__.py",
    "index.js", "server.js", "app.js", "main.js",
    "index.ts", "server.ts", "app.ts", "main.ts",
    "App.tsx", "App.jsx", "main.tsx", "main.jsx",
    "Main.java", "Application.java",
}

CONFIG_FILENAMES = {
    "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
    "setup.py", "setup.cfg", "pom.xml", "build.gradle", "settings.gradle",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".eslintrc", ".eslintrc.json", ".eslintrc.js", "ruff.toml", ".bandit",
}


class ProjectScanner:
    @staticmethod
    def is_excluded_path(rel_path: Path, excluded_dirs: Optional[List[str]] = None) -> bool:
        """Checks if any segment of rel_path matches excluded directory patterns."""
        dirs_to_check = set(excluded_dirs or settings.DEFAULT_EXCLUDED_DIRS)
        for part in rel_path.parts:
            if part in dirs_to_check:
                return True
        return False

    @staticmethod
    def count_lines_and_check_secrets(file_path: Path, rel_str: str) -> Dict[str, Any]:
        """Reads file, counts lines, and looks for hardcoded credentials."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = content.splitlines()
            loc = sum(1 for line in lines if line.strip() and not line.strip().startswith(("#", "//", "/*", "*")))
            
            secrets = detect_secrets_in_text(content, rel_str)
            return {
                "total_lines": len(lines),
                "loc": max(loc, 1),
                "has_secrets": len(secrets) > 0,
                "secrets_found": secrets,
                "content_preview": content[:2000]
            }
        except Exception:
            return {
                "total_lines": 0,
                "loc": 0,
                "has_secrets": False,
                "secrets_found": [],
                "content_preview": ""
            }

    @staticmethod
    def is_test_file(rel_path: Path) -> bool:
        name = rel_path.name.lower()
        parts = [p.lower() for p in rel_path.parts]
        
        if any(p in ("tests", "test", "__tests__", "spec") for p in parts):
            return True
        if name.startswith("test_") or name.endswith("_test.py") or name.endswith(".test.js") or name.endswith(".test.ts") or name.endswith(".spec.ts") or name.endswith(".spec.js"):
            return True
        return False

    @classmethod
    def scan_project(cls, project_dir: Path, custom_exclusions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scans an extracted directory to generate manifest items, language breakdown,
        LOC metrics, test file identification, and detected configurations.
        """
        manifest_items = []
        languages_count: Dict[str, int] = {}
        total_loc = 0
        total_files = 0
        configs_found = []
        test_files = []
        entry_points = []
        all_secrets = []

        project_dir = project_dir.resolve()

        for root, dirs, files in os.walk(project_dir):
            rel_root = Path(root).relative_to(project_dir)

            # Prune excluded directories in-place to optimize traversal
            dirs[:] = [
                d for d in dirs
                if not cls.is_excluded_path(rel_root / d, custom_exclusions)
            ]

            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_dir)
                rel_str = str(rel_path).replace("\\", "/")

                # Exclude if extension is ignored
                ext = file_path.suffix.lower()
                if ext in settings.DEFAULT_EXCLUDED_EXTENSIONS:
                    continue

                total_files += 1
                size = file_path.stat().st_size
                lang = LANGUAGE_EXTENSIONS.get(ext, "Other")

                is_test = cls.is_test_file(rel_path)
                if is_test:
                    test_files.append(rel_str)

                is_entry = file.lower() in {e.lower() for e in ENTRY_POINT_FILENAMES}
                if is_entry:
                    entry_points.append(rel_str)

                if file in CONFIG_FILENAMES:
                    configs_found.append(rel_str)

                # Count lines and check secrets
                stats = cls.count_lines_and_check_secrets(file_path, rel_str)
                total_loc += stats["loc"]
                
                if stats["has_secrets"]:
                    all_secrets.extend(stats["secrets_found"])

                languages_count[lang] = languages_count.get(lang, 0) + 1

                manifest_items.append({
                    "relative_path": rel_str,
                    "language": lang,
                    "lines_of_code": stats["loc"],
                    "size_bytes": size,
                    "is_test_file": is_test,
                    "is_entry_point": is_entry,
                    "has_secrets": stats["has_secrets"]
                })

        sorted_languages = sorted(
            [l for l in languages_count.keys() if l != "Other"],
            key=lambda l: languages_count[l],
            reverse=True
        )

        return {
            "total_files": total_files,
            "total_loc": total_loc,
            "detected_languages": sorted_languages,
            "language_distribution": languages_count,
            "configs_found": configs_found,
            "test_files": test_files,
            "entry_points": entry_points,
            "manifest_items": manifest_items,
            "secrets_detected": all_secrets
        }
