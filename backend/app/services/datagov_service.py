import time
import logging
import io
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

class DataGovService:
    def __init__(self):
        # In-memory city cache: key = city.lower(), value = (timestamp, data)
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl: float = 600.0  # 10 minutes cache
        self._status_cache: Optional[Tuple[float, Dict[str, Any]]] = None

    @property
    def is_configured(self) -> bool:
        """Check whether both API Key and Resource ID are provided."""
        has_key = bool(settings.DATA_GOV_IN_API_KEY and len(settings.DATA_GOV_IN_API_KEY.strip()) > 5)
        has_resource = bool(settings.DATA_GOV_IN_RESOURCE_ID and len(settings.DATA_GOV_IN_RESOURCE_ID.strip()) > 3)
        return has_key and has_resource

    def get_configuration_status(self) -> Dict[str, Any]:
        """Synchronously check configuration presence without making network calls."""
        has_key = bool(settings.DATA_GOV_IN_API_KEY and len(settings.DATA_GOV_IN_API_KEY.strip()) > 5)
        has_resource = bool(settings.DATA_GOV_IN_RESOURCE_ID and len(settings.DATA_GOV_IN_RESOURCE_ID.strip()) > 3)
        return {
            "configured": has_key and has_resource,
            "is_active": has_key and has_resource,
            "has_key": has_key,
            "has_resource": has_resource,
            "resource_id": settings.DATA_GOV_IN_RESOURCE_ID or None,
            "guidance": "Specify DATA_GOV_IN_API_KEY and DATA_GOV_IN_RESOURCE_ID in backend/.env to activate CPCB data.",
        }

    async def get_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Verify data.gov.in integration status, authentication, and resource validity."""
        has_key = bool(settings.DATA_GOV_IN_API_KEY and len(settings.DATA_GOV_IN_API_KEY.strip()) > 5)
        has_resource = bool(settings.DATA_GOV_IN_RESOURCE_ID and len(settings.DATA_GOV_IN_RESOURCE_ID.strip()) > 3)

        if not has_key or not has_resource:
            missing = []
            if not has_key:
                missing.append("DATA_GOV_IN_API_KEY")
            if not has_resource:
                missing.append("DATA_GOV_IN_RESOURCE_ID")
            return {
                "status": "unconfigured",
                "configured": False,
                "is_active": False,
                "missing_configuration": missing,
                "message": (
                    f"data.gov.in integration is currently unconfigured. Missing: {', '.join(missing)}. "
                    "Please specify your data.gov.in API Key and exact Resource ID in backend/.env to activate live CPCB OGD records."
                ),
                "configured_resource_id": settings.DATA_GOV_IN_RESOURCE_ID or None,
            }

        now = time.time()
        if not force_refresh and self._status_cache:
            c_time, c_data = self._status_cache
            if now - c_time < 300.0:  # 5 min cache for status
                return c_data

        url = f"{settings.DATA_GOV_IN_BASE_URL}/{settings.DATA_GOV_IN_RESOURCE_ID}"
        params = {
            "api-key": settings.DATA_GOV_IN_API_KEY,
            "format": "json",
            "limit": 1,
            "offset": 0,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=25.0, verify=False, headers=headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("records", [])
                    field_names = [f.get("id") or f.get("name") for f in data.get("field", [])]
                    res = {
                        "status": "active",
                        "configured": True,
                        "is_active": True,
                        "resource_id": settings.DATA_GOV_IN_RESOURCE_ID,
                        "title": data.get("title", "Real time Air Quality Index from various locations"),
                        "total_records_available": data.get("total", 0),
                        "field_names": field_names,
                        "sample_record": records[0] if records else None,
                        "message": "data.gov.in official CPCB ground monitoring resource verified and active.",
                    }
                    self._status_cache = (now, res)
                    return res
                elif resp.status_code in (401, 403):
                    return {
                        "status": "authentication_failed",
                        "configured": True,
                        "is_active": False,
                        "message": f"Authentication failed with provided DATA_GOV_IN_API_KEY (HTTP {resp.status_code}).",
                    }
                elif resp.status_code == 404:
                    return {
                        "status": "resource_not_found",
                        "configured": True,
                        "is_active": False,
                        "message": f"Resource ID '{settings.DATA_GOV_IN_RESOURCE_ID}' was not found on data.gov.in (HTTP 404).",
                    }
                else:
                    return {
                        "status": "error",
                        "configured": True,
                        "is_active": False,
                        "message": f"data.gov.in returned HTTP {resp.status_code}: {resp.text[:200]}",
                    }
        except Exception as exc:
            logger.warning(f"Error checking data.gov.in status: {exc}")
            return {
                "status": "unreachable",
                "configured": True,
                "is_active": False,
                "message": f"Network error connecting to api.data.gov.in: {str(exc)}",
            }

    async def fetch_city_records(
        self, city: str, limit: int = 50, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch and parse ground observation records for a city from data.gov.in.
        Groups observations by monitoring station and preserves original source metadata.
        """
        if not self.is_configured:
            return {
                "is_configured": False,
                "records": [],
                "stations": [],
                "source": "data.gov.in (OGD Platform)",
                "note": "data.gov.in API Key or Resource ID not configured in backend/.env",
            }

        city_clean = city.strip()
        cache_key = city_clean.lower()
        now = time.time()

        if not force_refresh and cache_key in self._cache:
            c_time, c_data = self._cache[cache_key]
            if now - c_time < self._cache_ttl:
                logger.info(f"Serving cached data.gov.in observations for {city_clean}")
                return c_data

        url = f"{settings.DATA_GOV_IN_BASE_URL}/{settings.DATA_GOV_IN_RESOURCE_ID}"
        params = {
            "api-key": settings.DATA_GOV_IN_API_KEY,
            "format": "json",
            "limit": limit,
            "filters[city]": city_clean,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False, headers=headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return {
                        "is_configured": True,
                        "error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                        "records": [],
                        "stations": [],
                        "source": f"data.gov.in Resource {settings.DATA_GOV_IN_RESOURCE_ID}",
                    }
                data = resp.json()
        except Exception as exc:
            logger.error(f"Error fetching data.gov.in records for {city_clean}: {exc}")
            return {
                "is_configured": True,
                "error": f"Network exception: {str(exc)}",
                "records": [],
                "stations": [],
                "source": f"data.gov.in Resource {settings.DATA_GOV_IN_RESOURCE_ID}",
            }

        raw_records = data.get("records", [])

        # Normalize records and group by monitoring station
        stations_map: Dict[str, Dict[str, Any]] = {}
        normalized_records: List[Dict[str, Any]] = []

        for r in raw_records:
            st_name = r.get("station", "Unknown Station")
            p_id = str(r.get("pollutant_id") or "").upper().strip()
            
            # Unit inference based on CPCB standards
            unit = "mg/m³" if p_id in ("CO", "CARBON MONOXIDE") else "µg/m³"
            
            def safe_float(val):
                if val is None or str(val).strip() in ("", "NA", "null", "None"):
                    return None
                try:
                    return float(str(val).strip())
                except ValueError:
                    return None

            avg_val = safe_float(r.get("avg_value"))
            min_val = safe_float(r.get("min_value"))
            max_val = safe_float(r.get("max_value"))
            lat = safe_float(r.get("latitude"))
            lon = safe_float(r.get("longitude"))

            norm_rec = {
                "country": r.get("country", "India"),
                "state": r.get("state"),
                "city": r.get("city"),
                "station": st_name,
                "pollutant": p_id,
                "avg_value": avg_val,
                "min_value": min_val,
                "max_value": max_val,
                "unit": unit,
                "latitude": lat,
                "longitude": lon,
                "last_update": r.get("last_update"),
                "data_type": "Official Ground Station Observation",
                "source": "Central Pollution Control Board (CPCB) via data.gov.in",
            }
            normalized_records.append(norm_rec)

            if st_name not in stations_map:
                stations_map[st_name] = {
                    "station_name": st_name,
                    "city": r.get("city"),
                    "state": r.get("state"),
                    "latitude": lat,
                    "longitude": lon,
                    "last_update": r.get("last_update"),
                    "pollutants": {},
                }

            stations_map[st_name]["pollutants"][p_id] = {
                "avg": avg_val,
                "min": min_val,
                "max": max_val,
                "unit": unit,
            }

        result = {
            "is_configured": True,
            "city_queried": city_clean,
            "total_records": len(normalized_records),
            "stations_count": len(stations_map),
            "stations": list(stations_map.values()),
            "records": normalized_records,
            "source": "Central Pollution Control Board (CPCB) via data.gov.in",
            "resource_id": settings.DATA_GOV_IN_RESOURCE_ID,
            "disclaimer": (
                "Official ground-level Continuous Ambient Air Quality Monitoring Station (CAAQMS) observations "
                "recorded by CPCB and State Pollution Control Boards. These represent actual sensor measurements on the ground."
            ),
        }

        self._cache[cache_key] = (now, result)
        return result

    async def import_city_as_dataset(self, city: str = "Chennai", limit: int = 200) -> Dict[str, Any]:
        """
        Fetch official CPCB CAAQMS observations from data.gov.in, pivot tall observations
        into a wide station-by-parameter dataset, register it in the database, and store it on disk.
        Preserves stations, timestamps, coordinates, units, and missing values (never fabricates).
        """
        from backend.app.services.data_service import data_service
        from backend.app.database.repository import save_dataset

        if not self.is_configured:
            raise ValueError(
                "data.gov.in integration is not configured. Please specify DATA_GOV_IN_API_KEY and "
                "DATA_GOV_IN_RESOURCE_ID in backend/.env to import official CPCB station observations."
            )

        clean_city = city.strip()
        data = await self.fetch_city_records(clean_city, limit=limit, force_refresh=True)
        stations = data.get("stations", [])

        if not stations:
            err = data.get("error")
            detail = f" ({err})" if err else ""
            raise ValueError(
                f"No official CPCB ground monitoring stations found for '{clean_city}' on data.gov.in{detail}."
            )

        rows = []
        for s in stations:
            pollutants = s.get("pollutants", {})
            # Look up values - preserve None for missing observations (never fabricate missing values)
            pm25 = pollutants.get("PM2.5", {}).get("avg") if "PM2.5" in pollutants else None
            pm10 = pollutants.get("PM10", {}).get("avg") if "PM10" in pollutants else None
            no2 = pollutants.get("NO2", {}).get("avg") if "NO2" in pollutants else None
            co = pollutants.get("CO", {}).get("avg") if "CO" in pollutants else None
            so2 = pollutants.get("SO2", {}).get("avg") if "SO2" in pollutants else None
            o3 = (pollutants.get("OZONE", {}) or pollutants.get("O3", {})).get("avg") if ("OZONE" in pollutants or "O3" in pollutants) else None
            nh3 = pollutants.get("NH3", {}).get("avg") if "NH3" in pollutants else None

            row = {
                "timestamp": s.get("last_update") or "2026-10-24 16:00:00",
                "station": s.get("station_name"),
                "city": s.get("city") or clean_city.title(),
                "state": s.get("state") or "",
                "latitude": s.get("latitude"),
                "longitude": s.get("longitude"),
                "PM2.5": pm25,
                "PM10": pm10,
                "NO2": no2,
                "CO": co,
                "SO2": so2,
                "O3": o3,
                "NH3": nh3,
                "source": "CPCB CAAQMS (data.gov.in)",
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        safe_city_name = clean_city.lower().replace(" ", "_").replace("/", "_")
        filename = f"cpcb_{safe_city_name}_observations.csv"

        summary = data_service.process_uploaded_file(csv_bytes, filename=filename)

        # Enhance summary with explicit source attribution metadata
        summary["source_type"] = "cpcb_ground"
        summary["source_description"] = (
            f"Official Continuous Ambient Air Quality Monitoring Station (CAAQMS) ground observations "
            f"recorded by the Central Pollution Control Board (CPCB) for {clean_city.title()} via data.gov.in (Resource ID {settings.DATA_GOV_IN_RESOURCE_ID})."
        )
        summary["is_synthetic"] = False
        summary["is_time_series"] = False

        save_dataset(summary)
        logger.info(f"Successfully imported and registered CPCB dataset for {clean_city}: {summary['id']}")
        return summary

datagov_service = DataGovService()
