import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

from backend.app.config import settings
from backend.app.services.open_meteo_service import open_meteo_service
from backend.app.services.tnpcb_service import tnpcb_service
from backend.app.services.datagov_service import datagov_service
from backend.app.services.ml_service import ml_service

logger = logging.getLogger(__name__)

# Curated reference index of prominent Indian metropolitan cities & industrial hubs
INDIAN_CITIES_INDEX: Dict[str, Dict[str, Any]] = {
    "chennai": {"name": "Chennai", "latitude": 13.0878, "longitude": 80.2785, "state": "Tamil Nadu", "district": "Chennai"},
    "delhi": {"name": "Delhi", "latitude": 28.6139, "longitude": 77.2090, "state": "Delhi", "district": "New Delhi"},
    "mumbai": {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "state": "Maharashtra", "district": "Mumbai"},
    "bengaluru": {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "state": "Karnataka", "district": "Bengaluru Urban"},
    "kolkata": {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "state": "West Bengal", "district": "Kolkata"},
    "hyderabad": {"name": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867, "state": "Telangana", "district": "Hyderabad"},
    "ahmedabad": {"name": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714, "state": "Gujarat", "district": "Ahmedabad"},
    "pune": {"name": "Pune", "latitude": 18.5204, "longitude": 73.8567, "state": "Maharashtra", "district": "Pune"},
    "jaipur": {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873, "state": "Rajasthan", "district": "Jaipur"},
    "lucknow": {"name": "Lucknow", "latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh", "district": "Lucknow"},
    "kanpur": {"name": "Kanpur", "latitude": 26.4499, "longitude": 80.3319, "state": "Uttar Pradesh", "district": "Kanpur Nagar"},
    "coimbatore": {"name": "Coimbatore", "latitude": 11.0168, "longitude": 76.9558, "state": "Tamil Nadu", "district": "Coimbatore"},
    "madurai": {"name": "Madurai", "latitude": 9.9252, "longitude": 78.1198, "state": "Tamil Nadu", "district": "Madurai"},
    "hosur": {"name": "Hosur", "latitude": 12.7409, "longitude": 77.8253, "state": "Tamil Nadu", "district": "Krishnagiri"},
    "thoothukudi": {"name": "Thoothukudi", "latitude": 8.7642, "longitude": 78.1348, "state": "Tamil Nadu", "district": "Thoothukudi"},
    "salem": {"name": "Salem", "latitude": 11.6643, "longitude": 78.1460, "state": "Tamil Nadu", "district": "Salem"},
    "tirunelveli": {"name": "Tirunelveli", "latitude": 8.7139, "longitude": 77.7567, "state": "Tamil Nadu", "district": "Tirunelveli"},
    "patna": {"name": "Patna", "latitude": 25.5941, "longitude": 85.1376, "state": "Bihar", "district": "Patna"},
    "chandigarh": {"name": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794, "state": "Chandigarh", "district": "Chandigarh"},
    "bhopal": {"name": "Bhopal", "latitude": 23.2599, "longitude": 77.4126, "state": "Madhya Pradesh", "district": "Bhopal"},
    "visakhapatnam": {"name": "Visakhapatnam", "latitude": 17.6868, "longitude": 83.2185, "state": "Andhra Pradesh", "district": "Visakhapatnam"},
}

class LocationService:
    async def search_indian_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search and resolve Indian cities and localities with validated coordinates."""
        q_clean = query.strip().lower()
        if not q_clean:
            # Return top default Indian metro cities
            return list(INDIAN_CITIES_INDEX.values())[:8]

        results = []
        # Check curated index first
        for key, item in INDIAN_CITIES_INDEX.items():
            if q_clean in key or q_clean in item["name"].lower() or q_clean in item.get("state", "").lower():
                results.append({
                    "name": item["name"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "state": item["state"],
                    "district": item["district"],
                    "country": "India",
                    "country_code": "IN",
                })

        # Query Open-Meteo Geocoding API specifically for India
        try:
            params = {
                "name": query,
                "count": 6,
                "country_code": "IN",
                "language": "en",
                "format": "json",
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(settings.OPEN_METEO_GEO_URL, params=params)
                if resp.status_code == 200:
                    geo = resp.json().get("results", [])
                    for g in geo:
                        name = g.get("name")
                        lat = float(g.get("latitude"))
                        lon = float(g.get("longitude"))
                        # Deduplicate by approximate distance
                        if not any(abs(r["latitude"] - lat) < 0.05 and abs(r["longitude"] - lon) < 0.05 for r in results):
                            results.append({
                                "name": name,
                                "latitude": lat,
                                "longitude": lon,
                                "state": g.get("admin1"),
                                "district": g.get("admin2"),
                                "country": "India",
                                "country_code": "IN",
                            })
        except Exception as e:
            logger.debug(f"Geocoding lookup error: {e}")

        return results[:10]

    async def get_city_air_quality(
        self,
        city_name: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Unified multi-source air quality evaluation for an Indian location.
        Integrates Open-Meteo, ML Model classification, TNPCB OCEMS industrial layer, and data.gov.in.
        """
        # Resolve coordinates if not provided
        resolved_name = city_name.strip()
        state = None
        district = None

        if lat is None or lon is None:
            matches = await self.search_indian_locations(city_name)
            if matches:
                lat = matches[0]["latitude"]
                lon = matches[0]["longitude"]
                resolved_name = matches[0]["name"]
                state = matches[0].get("state")
                district = matches[0].get("district")
            else:
                # Default to New Delhi if location completely unresolvable
                lat = 28.6139
                lon = 77.2090
                resolved_name = "Delhi"
                state = "Delhi"

        location_info = {
            "name": resolved_name,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "state": state,
            "district": district,
            "country": "India",
            "country_code": "IN",
        }

        sources_available = []
        source_disclaimers = {}

        # 1. Fetch Open-Meteo Modelled AQ
        open_meteo_data = None
        hourly_forecast = []
        ml_prediction = None

        try:
            om = await open_meteo_service.get_air_quality(lat, lon, force_refresh=force_refresh)
            open_meteo_data = om["current"]
            hourly_forecast = om["hourly_points"]
            sources_available.append("Open-Meteo Modelled Estimate")
            source_disclaimers["Open-Meteo"] = om["disclaimer"]

            # Run ML model on compatible Open-Meteo parameters
            # Model features: PM2.5, PM10, NO2, CO (mg/m3), SO2, O3
            ml_input = {
                "PM2.5": open_meteo_data["pm2_5"],
                "PM10": open_meteo_data["pm10"],
                "NO2": open_meteo_data["nitrogen_dioxide"],
                "CO": open_meteo_data["carbon_monoxide_mgm3"],
                "SO2": open_meteo_data["sulphur_dioxide"],
                "O3": open_meteo_data["ozone"],
            }
            ml_prediction = ml_service.predict(ml_input)
            sources_available.append("GreenAir RandomForest Model Classification")
            source_disclaimers["GreenAir_ML"] = ml_prediction["disclaimer"]

        except Exception as e:
            logger.error(f"Error getting Open-Meteo for {city_name}: {e}")

        # 2. Fetch TNPCB Industrial Records if location is in Tamil Nadu
        tnpcb_records = []
        is_tn = (state and "tamil nadu" in state.lower()) or (resolved_name.lower() in [
            "chennai", "coimbatore", "madurai", "hosur", "salem", "tirunelveli", "thoothukudi",
            "krishnagiri", "kallakurichi", "cuddalore", "erode", "kancheepuram", "chengalpattu"
        ])

        if is_tn:
            try:
                tnpcb_records = await tnpcb_service.get_industries_by_city(
                    resolved_name, emission_type_filter="air", only_active=False
                )
                if tnpcb_records:
                    sources_available.append("TNPCB OCEMS Industrial Monitoring")
                    source_disclaimers["TNPCB_OCEMS"] = (
                        "Important: TNPCB readings are measured at industrial stacks and discharge outlets (point sources). "
                        "They are NOT interchangeable with ambient city-wide air quality measurements."
                    )
            except Exception as e:
                logger.debug(f"TNPCB fetch error for {resolved_name}: {e}")

        # 3. Check data.gov.in
        datagov_info = None
        if datagov_service.is_configured:
            try:
                datagov_info = await datagov_service.fetch_city_records(resolved_name)
                if datagov_info.get("records"):
                    sources_available.append("data.gov.in (CPCB Ground Observations)")
                    source_disclaimers["data_gov_in"] = "Ground monitoring observations reported via data.gov.in OGD platform."
            except Exception:
                pass
        else:
            source_disclaimers["data_gov_in"] = "data.gov.in integration is unconfigured (requires DATA_GOV_IN_API_KEY and RESOURCE_ID in .env)."

        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "location": location_info,
            "sources_available": sources_available,
            "open_meteo": open_meteo_data,
            "ml_classification": ml_prediction,
            "hourly_forecast": hourly_forecast[:48],  # next 48 hours
            "data_gov_in": datagov_info,
            "tnpcb_industries": tnpcb_records[:20],  # top 20 for responsive view
            "retrieved_at": now_iso,
            "source_disclaimers": source_disclaimers,
        }

    async def compare_two_cities(self, city_1: str, city_2: str) -> Dict[str, Any]:
        """Side-by-side comparison of two Indian locations using compatible parameters."""
        data1 = await self.get_city_air_quality(city_1)
        data2 = await self.get_city_air_quality(city_2)

        loc1 = data1["location"]
        loc2 = data2["location"]
        r1 = data1.get("open_meteo")
        r2 = data2.get("open_meteo")

        metrics_comp = {}
        key_diffs = []

        if r1 and r2:
            params = [
                ("PM2.5", r1["pm2_5"], r2["pm2_5"], "µg/m³"),
                ("PM10", r1["pm10"], r2["pm10"], "µg/m³"),
                ("NO2", r1["nitrogen_dioxide"], r2["nitrogen_dioxide"], "µg/m³"),
                ("CO", r1["carbon_monoxide_mgm3"], r2["carbon_monoxide_mgm3"], "mg/m³"),
                ("SO2", r1["sulphur_dioxide"], r2["sulphur_dioxide"], "µg/m³"),
                ("O3", r1["ozone"], r2["ozone"], "µg/m³"),
            ]

            for name, v1, v2, unit in params:
                diff = round(v2 - v1, 2)
                pct = round(((v2 - v1) / max(v1, 0.01)) * 100, 1)
                metrics_comp[name] = {
                    loc1["name"]: v1,
                    loc2["name"]: v2,
                    "unit": unit,
                    "diff": diff,
                    "pct_change": pct,
                }
                if abs(pct) >= 15.0:
                    higher = loc2["name"] if diff > 0 else loc1["name"]
                    key_diffs.append(f"{name} is {abs(pct)}% higher in {higher} ({max(v1, v2)} {unit} vs {min(v1, v2)} {unit}).")

            if not key_diffs:
                key_diffs.append("Both locations exhibit closely comparable pollutant concentration baselines within a ±15% margin.")

        ml1 = data1.get("ml_classification", {}).get("category", "N/A")
        ml2 = data2.get("ml_classification", {}).get("category", "N/A")

        return {
            "city_1": loc1["name"],
            "city_2": loc2["name"],
            "location_1": loc1,
            "location_2": loc2,
            "reading_1": r1,
            "reading_2": r2,
            "ml_class_1": ml1,
            "ml_class_2": ml2,
            "comparison_metrics": metrics_comp,
            "key_differences": key_diffs,
            "limitations": (
                "Comparison is based on Open-Meteo numerical atmospheric model estimates retrieved at identical timestamps. "
                "Local micro-climates, sensor placement, and topological dispersion can influence actual localized exposures."
            ),
        }

location_service = LocationService()
