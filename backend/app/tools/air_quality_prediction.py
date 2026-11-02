from typing import Dict, Any, Union
from backend.app.services.ml_service import ml_service
from backend.app.database.repository import save_analysis_record

def predict_air_quality(
    pm25: Union[float, int],
    pm10: Union[float, int],
    no2: Union[float, int],
    co: Union[float, int],
    so2: Union[float, int],
    o3: Union[float, int],
) -> Dict[str, Any]:
    """
    Predict air quality category using the GreenAir trained Machine Learning model.
    Accepts 6 concentrations: PM2.5 (µg/m³), PM10 (µg/m³), NO2 (µg/m³), CO (mg/m³), SO2 (µg/m³), O3 (µg/m³).
    Inputs must be non-negative, finite numbers.
    """
    raw_inputs = {
        "PM2.5": float(pm25),
        "PM10": float(pm10),
        "NO2": float(no2),
        "CO": float(co),
        "SO2": float(so2),
        "O3": float(o3),
    }

    result = ml_service.predict(raw_inputs)

    # Save to analysis audit trail
    record_id = save_analysis_record(
        record_type="prediction",
        title=f"Air Quality Prediction: {result['category']}",
        input_summary=raw_inputs,
        result=result,
    )
    result["id"] = record_id

    return result
