import logging
from typing import Dict, Any, List, Optional
from backend.app.services.tnpcb_service import tnpcb_service

logger = logging.getLogger(__name__)

async def get_tnpcb_industrial_emissions(
    city: str,
    emission_type: str = "air",
    only_active: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve live industrial stack emissions and effluent monitoring observations from the TNPCB OCEMS public portal.
    Explicitly clarifies that stack emissions measured at factory outlets are NOT interchangeable with ambient city-wide AQI.
    """
    if not city or not city.strip():
        raise ValueError("City or district name must be provided to query TNPCB industrial monitoring.")

    logger.info(f"Tool get_tnpcb_industrial_emissions executing for city='{city}', emission_type='{emission_type}'")
    industries = await tnpcb_service.get_industries_by_city(
        city_name=city.strip(),
        emission_type_filter=emission_type if emission_type != "all" else None,
        only_active=only_active,
    )

    return {
        "city_queried": city.strip(),
        "emission_type_filter": emission_type,
        "industry_count": len(industries),
        "industries": industries[:25],  # top 25 records for tool context
        "data_source": "Tamil Nadu Pollution Control Board (TNPCB) Online Continuous Emission Monitoring System (OCEMS)",
        "disclaimer": (
            "CRITICAL NOTE: TNPCB measurements represent point-source industrial stack emissions and discharge parameters "
            "(e.g., SPM, SO2, NOx at stack flues). They do NOT represent ambient city air quality or general population exposure."
        ),
    }
