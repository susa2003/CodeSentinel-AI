from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.app.schemas.schemas import (
    LocationItem, CityAirQualityResponse, CityComparisonRequest, CityComparisonResponse
)
from backend.app.services.location_service import location_service

router = APIRouter(prefix="/locations", tags=["India Location Intelligence"])

@router.get("/search", response_model=List[LocationItem])
async def search_locations(query: str = Query(default="", description="Search term for Indian city or locality")):
    """Search and resolve Indian cities and localities to validated geographic coordinates."""
    results = await location_service.search_indian_locations(query)
    return results

@router.get("/{city}/live", response_model=CityAirQualityResponse)
async def get_city_air_quality(
    city: str,
    lat: Optional[float] = Query(default=None, description="Optional exact latitude"),
    lon: Optional[float] = Query(default=None, description="Optional exact longitude"),
    force_refresh: bool = Query(default=False, description="Bypass cache and force refresh from upstream"),
):
    """
    Retrieve unified live air quality for an Indian city or coordinate.
    Combines Open-Meteo numerical atmospheric estimates, GreenAir Random Forest ML classification,
    TNPCB OCEMS industrial monitoring (if in Tamil Nadu), and data.gov.in (if configured).
    """
    try:
        data = await location_service.get_city_air_quality(
            city_name=city,
            lat=lat,
            lon=lon,
            force_refresh=force_refresh,
        )
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live air quality for {city}: {str(exc)}")

@router.post("/compare", response_model=CityComparisonResponse)
async def compare_locations(req: CityComparisonRequest):
    """Compare air quality, pollutant baselines, and model categories between two Indian cities."""
    try:
        data = await location_service.compare_two_cities(req.city_1, req.city_2)
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(exc)}")
