from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None


class SystemSettingsResponse(BaseModel):
    settings: Dict[str, Any]
    environment: str
    active_llm_provider: str
    llm_has_api_key: bool
    installed_analyzers: Dict[str, bool]


class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    enable_ast: Optional[bool] = None
    enable_ruff: Optional[bool] = None
    enable_bandit: Optional[bool] = None
    enable_pattern_engine: Optional[bool] = None
    excluded_dirs: Optional[List[str]] = None


class LLMTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None


class LLMTestResponse(BaseModel):
    success: bool
    provider: str
    message: str
    latency_ms: Optional[float] = None
    is_demo_mode: bool = False
