from fastapi import APIRouter
from datetime import datetime, timezone
import os

from backend.app.config import settings
from backend.app.services.ml_service import ml_service
from backend.app.services.llm_service import llm_service
from backend.app.database.connection import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_system_health():
    """System health check and operational status."""
    # Database check
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1;").fetchone()
            db_ok = True
    except Exception:
        db_ok = False

    has_llm, provider = llm_service.is_provider_available()

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "type": "sqlite",
            "path": str(settings.DATABASE_PATH),
        },
        "model": {
            "loaded": ml_service.is_loaded,
            "type": ml_service.model_type,
            "is_fallback": ml_service.is_fallback,
            "classes": ml_service.classes,
        },
        "ai_engine": {
            "provider_available": has_llm,
            "active_provider": provider,
            "groq_configured": bool(settings.GROQ_API_KEY),
            "gemini_configured": bool(settings.GEMINI_API_KEY),
        },
    }
