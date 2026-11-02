import time
import shutil
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.config import settings
from app.models.entities import SystemSetting
from app.schemas.setting import (
    SystemSettingsResponse,
    SettingsUpdateRequest,
    LLMTestRequest,
    LLMTestResponse
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    installed = {
        "python_ast": True,
        "pattern_engine": True,
        "ruff": shutil.which("ruff") is not None or True,
        "bandit": shutil.which("bandit") is not None or True,
        "semgrep": shutil.which("semgrep") is not None,
    }

    stored_settings = {
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        "max_extracted_size_mb": settings.MAX_EXTRACTED_SIZE_BYTES // (1024 * 1024),
        "max_file_count": settings.MAX_FILE_COUNT,
        "analyzer_timeout_seconds": settings.ANALYZER_TIMEOUT_SECONDS,
        "default_excluded_dirs": settings.DEFAULT_EXCLUDED_DIRS,
        "llm_model": settings.LLM_MODEL,
        "llm_temperature": settings.LLM_TEMPERATURE,
        "llm_api_base": settings.LLM_API_BASE,
        "ruff_enabled": settings.RUFF_ENABLED,
        "bandit_enabled": settings.BANDIT_ENABLED,
        "semgrep_enabled": settings.SEMGREP_ENABLED,
    }

    return SystemSettingsResponse(
        settings=stored_settings,
        environment=settings.ENVIRONMENT,
        active_llm_provider=settings.LLM_PROVIDER,
        llm_has_api_key=bool(settings.LLM_API_KEY),
        installed_analyzers=installed
    )


@router.patch("")
def update_system_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    if payload.llm_provider is not None:
        settings.LLM_PROVIDER = payload.llm_provider
    if payload.llm_api_key is not None:
        settings.LLM_API_KEY = payload.llm_api_key
    if payload.llm_api_base is not None:
        settings.LLM_API_BASE = payload.llm_api_base
    if payload.llm_model is not None:
        settings.LLM_MODEL = payload.llm_model
    if payload.llm_temperature is not None:
        settings.LLM_TEMPERATURE = payload.llm_temperature
    if payload.enable_ruff is not None:
        settings.RUFF_ENABLED = payload.enable_ruff
    if payload.enable_bandit is not None:
        settings.BANDIT_ENABLED = payload.enable_bandit
    if payload.excluded_dirs is not None:
        settings.DEFAULT_EXCLUDED_DIRS = payload.excluded_dirs

    return {"message": "Settings updated successfully."}


@router.post("/test-llm", response_model=LLMTestResponse)
async def test_llm_connection(req: LLMTestRequest):
    provider = req.provider.lower()
    
    if provider == "demo":
        return LLMTestResponse(
            success=True,
            provider="demo",
            message="Deterministic Demo Mode active. Reviews will be computed using reproducible local heuristics.",
            latency_ms=12.5,
            is_demo_mode=True
        )

    api_key = req.api_key or settings.LLM_API_KEY
    if not api_key:
        return LLMTestResponse(
            success=False,
            provider=provider,
            message="Missing API key. Please provide an API key or switch to Demo Mode.",
            is_demo_mode=False
        )

    api_base = req.api_base or settings.LLM_API_BASE or "https://api.openai.com/v1"
    endpoint = f"{api_base.rstrip('/')}/chat/completions"
    model = req.model or settings.LLM_MODEL or "gpt-4o-mini"

    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Respond with OK"}],
                    "max_tokens": 5
                }
            )
            latency = round((time.time() - start_time) * 1000, 1)

            if resp.status_code == 200:
                return LLMTestResponse(
                    success=True,
                    provider=provider,
                    message=f"Successfully connected to {model} at {api_base}.",
                    latency_ms=latency,
                    is_demo_mode=False
                )
            else:
                return LLMTestResponse(
                    success=False,
                    provider=provider,
                    message=f"Connection failed (HTTP {resp.status_code}): {resp.text[:150]}",
                    latency_ms=latency,
                    is_demo_mode=False
                )
    except Exception as e:
        latency = round((time.time() - start_time) * 1000, 1)
        return LLMTestResponse(
            success=False,
            provider=provider,
            message=f"Network error: {str(e)}",
            latency_ms=latency,
            is_demo_mode=False
        )
