from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from backend.app.services.datagov_service import datagov_service

router = APIRouter(prefix="/datagov", tags=["data.gov.in Integration"])

@router.get("/status")
async def get_datagov_status():
    """Check data.gov.in integration status, configuration presence, and test API connectivity."""
    status = await datagov_service.get_status()
    return status

@router.get("/records")
async def get_datagov_records(
    city: str = Query(default="Delhi", description="City to query on data.gov.in"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Retrieve ground observation records from data.gov.in if configured."""
    data = await datagov_service.fetch_city_records(city=city, limit=limit)
    return data
