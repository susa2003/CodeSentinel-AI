import logging
from typing import Dict, Any
from backend.app.services.location_service import location_service

logger = logging.getLogger(__name__)

async def compare_cities(city_1: str, city_2: str) -> Dict[str, Any]:
    """
    Perform a side-by-side comparative analysis of air quality between two Indian cities.
    Evaluates pollutant concentrations, relative differences, dominant drivers, and GreenAir ML categories.
    """
    if not city_1 or not city_1.strip() or not city_2 or not city_2.strip():
        raise ValueError("Both city_1 and city_2 must be specified for comparison.")

    logger.info(f"Tool compare_cities executing for: '{city_1}' vs '{city_2}'")
    result = await location_service.compare_two_cities(city_1.strip(), city_2.strip())
    return result
