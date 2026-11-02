from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.app.schemas.schemas import (
    TrendAnalysisRequest, TrendAnalysisResponse,
    AnomalyDetectionRequest, AnomalyDetectionResponse,
    PollutantInput, PollutantAnalysisResponse,
    CompareRecordsRequest, CompareRecordsResponse,
    HealthGuidanceRequest, HealthGuidanceResponse,
)
from backend.app.tools.trend_analysis import analyze_trends
from backend.app.tools.anomaly_detection import detect_anomalies
from backend.app.tools.pollutant_analysis import analyze_pollutants
from backend.app.tools.compare_records import compare_records
from backend.app.tools.health_guidance import get_health_guidance

router = APIRouter(prefix="/analysis", tags=["Environmental Analytics"])

@router.post("/trends", response_model=TrendAnalysisResponse)
def get_trends(req: TrendAnalysisRequest):
    """Analyze time-series trends, slope, and trajectories."""
    try:
        return analyze_trends(
            dataset_id=req.dataset_id,
            pollutant=req.pollutant,
            rolling_window=req.rolling_window,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/anomalies", response_model=AnomalyDetectionResponse)
def get_anomalies(req: AnomalyDetectionRequest):
    """Detect statistical anomalies using IQR or Robust Z-Score bounds."""
    try:
        return detect_anomalies(
            dataset_id=req.dataset_id,
            pollutant=req.pollutant,
            method=req.method,
            threshold=req.multiplier,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/pollutants", response_model=PollutantAnalysisResponse)
def get_pollutant_analysis(pollutants: PollutantInput):
    """Analyze and rank pollutants against normalized ambient health benchmarks."""
    try:
        return analyze_pollutants(
            pm25=pollutants.pm25,
            pm10=pollutants.pm10,
            no2=pollutants.no2,
            co=pollutants.co,
            so2=pollutants.so2,
            o3=pollutants.o3,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/compare", response_model=CompareRecordsResponse)
def get_record_comparison(req: CompareRecordsRequest):
    """Compare multiple datasets or prediction records side by side."""
    try:
        return compare_records(
            dataset_ids=req.dataset_ids,
            prediction_ids=req.prediction_ids,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/guidance", response_model=HealthGuidanceResponse)
def get_guidance(req: HealthGuidanceRequest):
    """Obtain evidence-based health guidance for an air quality classification."""
    try:
        dominant = None
        if req.pollutants:
            # find max ratio
            dominant = max(req.pollutants.items(), key=lambda x: x[1])[0]
        return get_health_guidance(category=req.category, dominant_pollutant=dominant)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
