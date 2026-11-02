from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from backend.app.schemas.schemas import PollutantInput, PredictionResponse
from backend.app.tools.air_quality_prediction import predict_air_quality

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.post("", response_model=PredictionResponse)
def create_prediction(pollutants: PollutantInput):
    """
    Generate an air quality classification prediction from 6 input pollutants.
    Features: PM2.5, PM10, NO2, CO, SO2, O3.
    """
    try:
        result = predict_air_quality(
            pm25=pollutants.pm25,
            pm10=pollutants.pm10,
            no2=pollutants.no2,
            co=pollutants.co,
            so2=pollutants.so2,
            o3=pollutants.o3,
        )
        result["created_at"] = datetime.now(timezone.utc).isoformat()
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(exc)}")
