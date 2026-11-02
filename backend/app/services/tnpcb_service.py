import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

class TNPCBService:
    def __init__(self):
        self._industries_cache: Optional[List[Dict[str, Any]]] = None
        self._cities_cache: Optional[List[str]] = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 600.0  # 10 minutes cache

    async def _fetch_all_industries(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all public industry OCEMS records from the verified TNPCB API endpoint."""
        now = time.time()
        if not force_refresh and self._industries_cache is not None and (now - self._cache_time < self._cache_ttl):
            return self._industries_cache

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
                resp = await client.post(settings.TNPCB_OCEMS_URL, headers=headers, json={})
                if resp.status_code != 200:
                    logger.error(f"TNPCB API returned status {resp.status_code}: {resp.text[:200]}")
                    if self._industries_cache:
                        return self._industries_cache
                    return []
                data = resp.json()
                raw_industries = data.get("data", [])
        except Exception as exc:
            logger.error(f"Error connecting to TNPCB portal: {exc}")
            if self._industries_cache:
                return self._industries_cache
            return []

        cleaned_list = []
        for ind in raw_industries:
            cleaned = self._clean_industry_record(ind)
            if cleaned:
                cleaned_list.append(cleaned)

        self._industries_cache = cleaned_list
        self._cache_time = now
        logger.info(f"Loaded {len(cleaned_list)} industries from TNPCB OCEMS public endpoint.")
        return cleaned_list

    def _clean_industry_record(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse, sanitize, and validate a single raw TNPCB industry dictionary."""
        try:
            ind_id = int(raw.get("id") or 0)
            if not ind_id:
                return None

            name = str(raw.get("name") or "").strip()
            city = str(raw.get("city") or "").strip()
            address = str(raw.get("address") or "").strip()
            emission_type = str(raw.get("emmision_type") or "unknown").strip().lower()

            lat = None
            lon = None
            try:
                if raw.get("latitude"):
                    lat = float(str(raw["latitude"]).strip())
                if raw.get("longitude"):
                    lon = float(str(raw["longitude"]).strip())
            except (ValueError, TypeError):
                lat = None
                lon = None

            # Parse parameter_values JSON string
            pv_raw = raw.get("parameter_values")
            parsed_params = []
            if pv_raw:
                try:
                    pvs = json.loads(pv_raw) if isinstance(pv_raw, str) else pv_raw
                    if isinstance(pvs, list):
                        for p in pvs:
                            if isinstance(p, dict):
                                p_name = str(p.get("name") or "").strip()
                                curr_str = p.get("current")
                                curr_val = None
                                if curr_str is not None and str(curr_str).strip() not in ("", "null", "None"):
                                    try:
                                        curr_val = float(str(curr_str).strip())
                                    except ValueError:
                                        curr_val = None

                                # Unit inference
                                unit = "mg/Nm³"
                                if p_name.upper() in ("SO2", "NOX", "NO2", "CO", "SPM", "PM"):
                                    unit = "mg/Nm³"
                                elif p_name.upper() in ("TVOC", "VOC"):
                                    unit = "ppm"
                                elif p_name.upper() in ("O2",):
                                    unit = "%"
                                elif p_name.upper() in ("FLOW",):
                                    unit = "m³/hr"
                                elif p_name.upper() in ("PH",):
                                    unit = "pH units"
                                elif p_name.upper() in ("BOD", "COD", "TSS"):
                                    unit = "mg/L"

                                # Min and max parsing with safe float conversion
                                min_val = None
                                max_val = None
                                try:
                                    if p.get("min") not in (None, "", "null", "None"):
                                        min_val = float(str(p["min"]).strip())
                                except (ValueError, TypeError):
                                    min_val = None
                                try:
                                    if p.get("max") not in (None, "", "null", "None"):
                                        max_val = float(str(p["max"]).strip())
                                except (ValueError, TypeError):
                                    max_val = None

                                parsed_params.append({
                                    "name": p_name,
                                    "current": curr_val,
                                    "unit": unit,
                                    "min": min_val,
                                    "max": max_val,
                                })
                except Exception as parse_err:
                    logger.debug(f"Could not parse parameter_values for {name}: {parse_err}")

            return {
                "id": ind_id,
                "name": name,
                "city": city,
                "address": address,
                "industry_type": raw.get("industry_type"),
                "emmision_type": emission_type,
                "industry_category": raw.get("industry_category"),
                "latitude": lat,
                "longitude": lon,
                "spcb_regional_office": raw.get("spcb_regional_office"),
                "parameters": parsed_params,
                "last_update_date": raw.get("last_update_date") or raw.get("created_date"),
                "data_type": "Industrial Stack Emission (Point Source, Non-Ambient)",
                "source": "Tamil Nadu Pollution Control Board (TNPCB OCEMS)",
            }
        except Exception as e:
            logger.debug(f"Error cleaning industry: {e}")
            return None

    async def get_cities(self) -> List[str]:
        """List distinct cities and districts present in TNPCB records."""
        industries = await self._fetch_all_industries()
        cities = sorted(list(set(ind["city"] for ind in industries if ind.get("city"))))
        return cities

    async def get_industries_by_city(
        self,
        city: str = "",
        emission_type_filter: str = "all",
        only_active: bool = False,
        city_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query industrial records for a specific city or district in Tamil Nadu.
        Supports filtering by emission type ('air', 'water', 'both', 'all').
        """
        all_inds = await self._fetch_all_industries()
        target_city = (city_name or city).strip().lower()

        filtered = []
        for ind in all_inds:
            ind_city = ind["city"].lower()
            if target_city in ind_city or ind_city in target_city:
                etype = ind["emmision_type"]
                if emission_type_filter != "all":
                    if emission_type_filter == "air" and not ("air" in etype or "both" in etype):
                        continue
                    elif emission_type_filter == "water" and not ("water" in etype or "both" in etype):
                        continue

                if only_active:
                    has_val = any(p.get("current") is not None for p in ind["parameters"])
                    if not has_val:
                        continue

                filtered.append(ind)

        return filtered

tnpcb_service = TNPCBService()
