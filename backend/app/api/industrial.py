from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.app.schemas.schemas import IndustryRecord
from backend.app.services.tnpcb_service import tnpcb_service

router = APIRouter(prefix="/industrial", tags=["Industrial Monitoring (TNPCB OCEMS)"])

@router.get("/tnpcb/cities", response_model=List[str])
async def get_tnpcb_cities():
    """List all Tamil Nadu cities and districts with registered online continuous emission monitoring (OCEMS) industries."""
    try:
        cities = await tnpcb_service.get_cities()
        return cities
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TNPCB cities: {str(exc)}")

@router.get("/tnpcb/industries", response_model=List[IndustryRecord])
async def get_tnpcb_industries(
    city: str = Query(default="Chennai", description="Tamil Nadu city or district name"),
    emission_type: str = Query(default="all", enum=["air", "water", "both", "all"]),
    only_active: bool = Query(default=False, description="Filter only industries with active current readings"),
):
    """
    Retrieve real-time stack emission and effluent monitoring records from TNPCB OCEMS.
    NOTICE: Stack emissions represent point-source industrial exhaust and are NOT interchangeable with ambient city air quality.
    """
    try:
        industries = await tnpcb_service.get_industries_by_city(
            city=city,
            emission_type_filter=emission_type,
            only_active=only_active,
        )
        return industries
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query TNPCB industries: {str(exc)}")
