import time
import logging
from typing import Dict, Any, Optional, List, Tuple
import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

class OpenMeteoService:
    def __init__(self):
        # In-memory coordinate cache: key = f"{lat:.3f}_{lon:.3f}", value = (timestamp, data)
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl_seconds = 900  # 15 minutes cache

    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch current modelled air quality estimates and hourly forecasts from Open-Meteo API.
        Applies caching, documented unit normalization, and source preservation.
        """
        cache_key = f"{latitude:.3f}_{longitude:.3f}"
        now = time.time()

        if not force_refresh and cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if now - cached_time < self._cache_ttl_seconds:
                logger.info(f"Serving Open-Meteo data from cache for {cache_key}")
                return cached_data

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,european_aqi,us_aqi",
            "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,european_aqi,us_aqi",
            "timezone": "Asia/Kolkata",
            "forecast_days": 3,
            "past_days": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                resp = await client.get(settings.OPEN_METEO_AQ_URL, params=params)
                if resp.status_code != 200:
                    raise RuntimeError(f"Open-Meteo API returned status {resp.status_code}: {resp.text[:200]}")
                raw = resp.json()
        except httpx.TimeoutException:
            logger.error("Open-Meteo API request timed out.")
            raise TimeoutError("Open-Meteo Air Quality service timed out. Please retry.")
        except Exception as e:
            logger.error(f"Failed to fetch Open-Meteo data: {e}")
            raise RuntimeError(f"Open-Meteo service error: {str(e)}")

        current_raw = raw.get("current", {})
        units_raw = raw.get("current_units", {})
        hourly_raw = raw.get("hourly", {})

        # Documented unit conversion: CO is returned in ug/m3.
        # 1000 ug/m3 = 1.0 mg/m3.
        co_ugm3 = float(current_raw.get("carbon_monoxide") or 0.0)
        co_mgm3 = round(co_ugm3 / 1000.0, 3)

        current_reading = {
            "time": str(current_raw.get("time")),
            "pm2_5": float(current_raw.get("pm2_5") or 0.0),
            "pm10": float(current_raw.get("pm10") or 0.0),
            "nitrogen_dioxide": float(current_raw.get("nitrogen_dioxide") or 0.0),
            "carbon_monoxide_ugm3": co_ugm3,
            "carbon_monoxide_mgm3": co_mgm3,
            "sulphur_dioxide": float(current_raw.get("sulphur_dioxide") or 0.0),
            "ozone": float(current_raw.get("ozone") or 0.0),
            "european_aqi": current_raw.get("european_aqi"),
            "us_aqi": current_raw.get("us_aqi"),
            "data_type": "Modelled Atmospheric Estimate",
            "source": "Open-Meteo Air Quality Model (CAMS / SILAM / EMEP ensemble)",
            "units": {
                "pm2_5": "µg/m³",
                "pm10": "µg/m³",
                "nitrogen_dioxide": "µg/m³",
                "carbon_monoxide": "mg/m³ (converted from µg/m³ ÷ 1000)",
                "sulphur_dioxide": "µg/m³",
                "ozone": "µg/m³",
                "european_aqi": "EAQI (Modelled Scale)",
                "us_aqi": "USAQI (Modelled Scale)",
            },
        }

        # Parse hourly forecast points (next 72 hours)
        times = hourly_raw.get("time", [])
        pm25_list = hourly_raw.get("pm2_5", [])
        pm10_list = hourly_raw.get("pm10", [])
        no2_list = hourly_raw.get("nitrogen_dioxide", [])
        so2_list = hourly_raw.get("sulphur_dioxide", [])
        co_list = hourly_raw.get("carbon_monoxide", [])
        o3_list = hourly_raw.get("ozone", [])
        us_aqi_list = hourly_raw.get("us_aqi", [])

        hourly_points = []
        for i in range(len(times)):
            try:
                co_val = float(co_list[i]) if i < len(co_list) and co_list[i] is not None else 0.0
                hourly_points.append({
                    "time": str(times[i]),
                    "pm2_5": float(pm25_list[i]) if i < len(pm25_list) and pm25_list[i] is not None else 0.0,
                    "pm10": float(pm10_list[i]) if i < len(pm10_list) and pm10_list[i] is not None else 0.0,
                    "nitrogen_dioxide": float(no2_list[i]) if i < len(no2_list) and no2_list[i] is not None else 0.0,
                    "carbon_monoxide": round(co_val / 1000.0, 3),
                    "sulphur_dioxide": float(so2_list[i]) if i < len(so2_list) and so2_list[i] is not None else 0.0,
                    "ozone": float(o3_list[i]) if i < len(o3_list) and o3_list[i] is not None else 0.0,
                    "us_aqi": us_aqi_list[i] if i < len(us_aqi_list) else None,
                })
            except Exception:
                continue

        result = {
            "latitude": latitude,
            "longitude": longitude,
            "current": current_reading,
            "hourly_points": hourly_points,
            "cached": False,
            "disclaimer": (
                "Open-Meteo values are numerical atmospheric model estimates (CAMS/SILAM ensemble) "
                "with 11km grid resolution. They reflect modelled atmospheric concentrations rather than direct "
                "continuous ambient ground station monitoring (CPCB CAAQMS) or official regulatory Indian AQI determinations."
            ),
        }

        self._cache[cache_key] = (now, result)
        return result

    async def import_city_as_dataset(self, city: str, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch 72-hour hourly atmospheric forecast and history from Open-Meteo,
        convert into a time-series tabular dataset, register it in the database, and store it on disk.
        """
        import pandas as pd
        from backend.app.services.data_service import data_service
        from backend.app.database.repository import save_dataset

        clean_city = city.strip()
        data = await self.get_air_quality(latitude, longitude, force_refresh=True)
        hourly_points = data.get("hourly_points", [])

        if not hourly_points:
            raise ValueError(f"No hourly points returned by Open-Meteo for {clean_city} ({latitude}, {longitude}).")

        rows = []
        for pt in hourly_points:
            rows.append({
                "timestamp": pt.get("time"),
                "location": clean_city.title(),
                "latitude": latitude,
                "longitude": longitude,
                "PM2.5": pt.get("pm2_5"),
                "PM10": pt.get("pm10"),
                "NO2": pt.get("nitrogen_dioxide"),
                "CO": pt.get("carbon_monoxide"),
                "SO2": pt.get("sulphur_dioxide"),
                "O3": pt.get("ozone"),
                "US_AQI": pt.get("us_aqi"),
                "source": "Open-Meteo Atmospheric Model (CAMS/SILAM ensemble)",
            })

        df = pd.DataFrame(rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        safe_city_name = clean_city.lower().replace(" ", "_").replace("/", "_")
        filename = f"openmeteo_{safe_city_name}_72h_series.csv"

        summary = data_service.process_uploaded_file(csv_bytes, filename=filename)

        summary["source_type"] = "open_meteo_model"
        summary["source_description"] = (
            f"Open-Meteo atmospheric chemistry numerical model ensemble (CAMS/SILAM) "
            f"72-hour forecast and historical time-series for {clean_city.title()} ({latitude:.2f}°N, {longitude:.2f}°E)."
        )
        summary["is_synthetic"] = False
        summary["is_time_series"] = True

        save_dataset(summary)
        logger.info(f"Successfully imported Open-Meteo 72h dataset for {clean_city}: {summary['id']}")
        return summary

open_meteo_service = OpenMeteoService()
