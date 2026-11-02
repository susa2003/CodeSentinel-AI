from pathlib import Path
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeSentinel AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database (SQLite default for initial dev, Postgres-ready)
    DATABASE_URL: str = "sqlite:///./codesentinel.db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Storage paths
    BASE_STORAGE_DIR: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    EXTRACTED_DIR: Path = Path("./storage/extracted")
    REPORTS_DIR: Path = Path("./storage/reports")

    # Upload & Security limits
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_EXTRACTED_SIZE_BYTES: int = 200 * 1024 * 1024  # 200 MB
    MAX_FILE_COUNT: int = 2500
    MAX_SINGLE_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    MAX_DECOMPRESSION_RATIO: float = 50.0  # Zip bomb prevention

    # Exclusion patterns (directories & file patterns to ignore)
    DEFAULT_EXCLUDED_DIRS: List[str] = [
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "dist",
        "build",
        "out",
        "target",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "coverage",
        ".nyc_output",
        "vendor",
        ".idea",
        ".vscode",
        ".next",
        ".nuxt",
    ]

    DEFAULT_EXCLUDED_EXTENSIONS: List[str] = [
        ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe",
        ".zip", ".tar", ".gz", ".7z", ".rar",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
        ".mp3", ".mp4", ".wav", ".avi", ".mov",
        ".woff", ".woff2", ".ttf", ".eot",
        ".db", ".sqlite", ".sqlite3",
        ".pdf", ".docx", ".xlsx",
    ]

    # Analyzer configuration
    ANALYZER_TIMEOUT_SECONDS: int = 60
    RUFF_ENABLED: bool = True
    BANDIT_ENABLED: bool = True
    SEMGREP_ENABLED: bool = True
    PYTHON_AST_ENABLED: bool = True
    PATTERN_ENGINE_ENABLED: bool = True
    CROSS_FILE_ENABLED: bool = True

    # LLM Settings
    LLM_PROVIDER: str = "demo"  # "demo", "openai", "gemini", "custom"
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_CONTEXT_TOKENS: int = 8000
    LLM_MAX_TARGETED_FILES: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Ensure critical directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
