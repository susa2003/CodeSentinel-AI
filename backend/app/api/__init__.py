from fastapi import APIRouter
from app.api.projects import router as projects_router
from app.api.analyses import router as analyses_router
from app.api.findings import router as findings_router
from app.api.reports import router as reports_router
from app.api.settings import router as settings_router
from app.api.stats import router as stats_router

api_router = APIRouter()

api_router.include_router(projects_router)
api_router.include_router(analyses_router)
api_router.include_router(findings_router)
api_router.include_router(reports_router)
api_router.include_router(settings_router)
api_router.include_router(stats_router)
