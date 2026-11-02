import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BASE_DIR.parent

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "GreenAir AI Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    WORKSPACE_ROOT: Path = WORKSPACE_ROOT
    
    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # "groq", "gemini", or "auto"
    
    # External Air Quality & Industrial APIs
    DATA_GOV_IN_API_KEY: str = os.getenv("DATA_GOV_IN_API_KEY", "")
    DATA_GOV_IN_RESOURCE_ID: str = os.getenv("DATA_GOV_IN_RESOURCE_ID", "")
    DATA_GOV_IN_BASE_URL: str = "https://api.data.gov.in/resource"
    
    OPEN_METEO_AQ_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_GEO_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    
    TNPCB_OCEMS_URL: str = "https://tnpcb.gov.in/ocems/tncpcb-api/api/get-all-industry-details-public"
    TNPCB_CITY_LIST_URL: str = "https://tnpcb.gov.in/ocems/tncpcb-api/api/get-all-city-list-public"
    TNPCB_PROFILE_URL: str = "https://tnpcb.gov.in/ocems/tncpcb-api/api/get-industry-profile-details-public"
    TNPCB_DEVICE_URL: str = "https://tnpcb.gov.in/ocems/tncpcb-api/api/get-industry-station-device-details-public"
    
    # Storage & Database
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    REPORTS_DIR: Path = BASE_DIR / "data" / "reports"
    DATABASE_PATH: Path = BASE_DIR / "data" / "greenair.db"
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"
    
    # Model configuration
    # Check prioritized potential locations for greenair_model.pkl
    MODEL_LOCATIONS: List[Path] = [
        BASE_DIR / "model" / "greenair_model.pkl",
        WORKSPACE_ROOT / "greenair-project-main" / "greenair_model.pkl",
        WORKSPACE_ROOT / "greenair_model.pkl",
        BASE_DIR / "greenair_model.pkl"
    ]
    
    # File limits
    MAX_UPLOAD_SIZE_MB: int = 15
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]
    
    # Agent Guardrails
    MAX_AGENT_ITERATIONS: int = 6
    REQUEST_TIMEOUT_SECONDS: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    class Config:
        env_file = [str(BASE_DIR / ".env"), str(WORKSPACE_ROOT / ".env"), ".env"]
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "model").mkdir(parents=True, exist_ok=True)
