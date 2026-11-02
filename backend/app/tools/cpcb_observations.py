import logging
from typing import Dict, Any
from backend.app.services.datagov_service import datagov_service

logger = logging.getLogger(__name__)

async def get_cpcb_ground_observations(city: str) -> Dict[str, Any]:
    """
    Retrieve real-time official ground-level continuous ambient air quality monitoring station (CAAQMS)
    observations published by the Central Pollution Control Board (CPCB) via data.gov.in.
    Returns monitoring stations, specific pollutant measurements (PM2.5, PM10, NO2, SO2, CO, Ozone),
    coordinates, and last update timestamps.
    """
    if not city or not city.strip():
        raise ValueError("City name must be provided to query CPCB ground observations.")

    city_clean = city.strip()
    logger.info(f"Tool get_cpcb_ground_observations executing for city='{city_clean}'")

    if not datagov_service.is_configured:
        return {
            "status": "unconfigured",
            "city": city_clean,
            "stations_count": 0,
            "stations": [],
            "message": "data.gov.in integration is not configured with DATA_GOV_IN_API_KEY and DATA_GOV_IN_RESOURCE_ID.",
        }

    data = await datagov_service.fetch_city_records(city_clean)
    return data
