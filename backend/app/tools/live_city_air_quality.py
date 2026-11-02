import logging
from typing import Dict, Any, Optional
from backend.app.services.location_service import location_service

logger = logging.getLogger(__name__)

async def get_live_city_air_quality(city: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retrieve real-time atmospheric air quality data, 72-hour hourly forecasts,
    GreenAir ML model classification, and local industrial monitoring records for an Indian city or locality.
    Distinguishes Open-Meteo numerical model estimates from TNPCB stack emissions and CPCB observations.
    """
    if not city or not city.strip():
        raise ValueError("City name or locality must be provided.")
    
    logger.info(f"Tool get_live_city_air_quality executing for: {city}")
    result = await location_service.get_city_air_quality(city_name=city.strip(), force_refresh=force_refresh)
    return result
