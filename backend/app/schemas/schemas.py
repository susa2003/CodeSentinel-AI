from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
import math

class PollutantInput(BaseModel):
    pm25: float = Field(..., alias="PM2.5", ge=0.0, description="PM2.5 particulate matter in µg/m³")
    pm10: float = Field(..., alias="PM10", ge=0.0, description="PM10 particulate matter in µg/m³")
    no2: float = Field(..., alias="NO2", ge=0.0, description="Nitrogen Dioxide in µg/m³ or ppb")
    co: float = Field(..., alias="CO", ge=0.0, description="Carbon Monoxide in mg/m³ or ppm")
    so2: float = Field(..., alias="SO2", ge=0.0, description="Sulfur Dioxide in µg/m³ or ppb")
    o3: float = Field(..., alias="O3", ge=0.0, description="Ground-level Ozone in µg/m³ or ppb")

    @field_validator("pm25", "pm10", "no2", "co", "so2", "o3", mode="before")
    def validate_numeric_finite(cls, v):
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("All pollutant values must be valid numbers")
        if math.isnan(val) or math.isinf(val):
            raise ValueError("Pollutant values cannot be NaN or Infinite")
        if val < 0:
            raise ValueError("Pollutant values must be non-negative")
        return val

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "PM2.5": 35.5,
                "PM10": 65.0,
                "NO2": 24.2,
                "CO": 0.8,
                "SO2": 12.0,
                "O3": 42.1
            }
        }

class PredictionResponse(BaseModel):
    id: Optional[str] = None
    category: str
    probabilities: Dict[str, float]
    confidence_pct: float
    input_values: Dict[str, float]
    model_name: str
    model_type: str
    is_fallback: bool = False
    disclaimer: str
    health_guidance: str
    status_color: str
    created_at: str

class PollutantMetric(BaseModel):
    pollutant: str
    value: float
    unit: str
    standard_benchmark: float
    benchmark_ratio: float
    benchmark_source: str
    status: str
    description: str

class PollutantAnalysisResponse(BaseModel):
    dominant_pollutant: str
    highest_relative_pollutant: str
    highest_benchmark_ratio: float = 0.0
    metrics: List[PollutantMetric]
    attention_flags: List[str]
    summary_text: str
    scientific_context: str

class DatasetSummary(BaseModel):
    id: str
    filename: str
    stored_path: str
    row_count: int
    column_count: int
    columns: List[str]
    pollutant_columns: List[str]
    has_timestamps: bool
    timestamp_column: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    missing_values_count: int
    duplicate_rows_count: int
    data_quality_score: float
    quality_warnings: List[str]
    pollutant_stats: Dict[str, Dict[str, float]]
    preview_rows: List[Dict[str, Any]]
    created_at: str
    source_type: Optional[str] = "upload"  # "cpcb_ground", "open_meteo_model", "synthetic_demo", "upload"
    source_description: Optional[str] = None
    is_synthetic: Optional[bool] = False
    is_time_series: Optional[bool] = True

class TrendPoint(BaseModel):
    timestamp: str
    value: float
    rolling_avg: Optional[float] = None

class TrendAnalysisRequest(BaseModel):
    dataset_id: str
    pollutant: str = "PM2.5"
    rolling_window: int = 3

class TrendAnalysisResponse(BaseModel):
    pollutant: str
    trend_direction: str  # "Increasing", "Decreasing", "Stable", "Inconclusive"
    slope: float
    change_percentage: float
    initial_value: float
    final_value: float
    min_value: float
    max_value: float
    mean_value: float
    point_count: int
    coverage_note: str
    data_points: List[TrendPoint]

class AnomalyRecord(BaseModel):
    row_index: int
    timestamp: Optional[str] = None
    pollutant: str
    value: float
    threshold_low: float
    threshold_high: float
    score: float
    severity: str  # "Low", "Moderate", "High"
    explanation: str

class AnomalyDetectionRequest(BaseModel):
    dataset_id: str
    pollutant: str = "PM2.5"
    method: str = "iqr"  # "iqr" or "zscore"
    multiplier: float = 1.5

class AnomalyDetectionResponse(BaseModel):
    dataset_id: str
    pollutant: str
    method: str
    total_records_examined: int
    anomaly_count: int
    anomaly_percentage: float
    lower_bound: float
    upper_bound: float
    anomalies: List[AnomalyRecord]
    interpretation_note: str

class HealthGuidanceRequest(BaseModel):
    category: str
    pollutants: Optional[Dict[str, float]] = None

class HealthGuidanceResponse(BaseModel):
    category: str
    general_guidance: str
    vulnerable_populations: str
    outdoor_activities: str
    indoor_precautions: str
    authoritative_sources: List[str]
    disclaimer: str

class ReportRequest(BaseModel):
    report_type: str = "pdf"  # "pdf" or "csv"
    title: Optional[str] = "GreenAir Environmental Assessment Report"
    dataset_id: Optional[str] = None
    prediction_id: Optional[str] = None
    pollutant_inputs: Optional[Dict[str, float]] = None
    include_anomalies: bool = True
    include_trends: bool = True

class ReportResponse(BaseModel):
    report_id: str
    filename: str
    file_type: str
    size_bytes: int
    download_url: str
    title: str
    generated_at: str
    summary_findings: List[str]

class ToolExecutionRecord(BaseModel):
    tool_name: str
    tool_arguments: Dict[str, Any]
    output: Any
    execution_time_ms: float
    success: bool
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    active_dataset_id: Optional[str] = None
    latest_pollutants: Optional[Dict[str, float]] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tools_executed: List[ToolExecutionRecord]
    data_references: Dict[str, Any]
    provider_used: str
    finish_reason: str
    created_at: str

class SessionSummary(BaseModel):
    session_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str

class CompareRecordsRequest(BaseModel):
    dataset_ids: Optional[List[str]] = None
    prediction_ids: Optional[List[str]] = None

class CompareRecordsResponse(BaseModel):
    comparison_type: str
    compared_entities: List[str]
    metrics_comparison: Dict[str, Dict[str, Any]]
    key_differences: List[str]
    limitations: str

# --- India Location Intelligence & Multi-Source Schemas ---

class LocationItem(BaseModel):
    name: str
    latitude: float
    longitude: float
    state: Optional[str] = None
    district: Optional[str] = None
    country: str = "India"
    country_code: str = "IN"

class IndustryEmissionParameter(BaseModel):
    name: str
    current: Optional[float] = None
    unit: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None

class IndustryRecord(BaseModel):
    id: int
    name: str
    city: str
    address: Optional[str] = None
    industry_type: Optional[str] = None
    emmision_type: Optional[str] = None
    industry_category: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    spcb_regional_office: Optional[str] = None
    parameters: List[IndustryEmissionParameter] = []
    last_update_date: Optional[str] = None
    data_type: str = "Industrial Stack Emission (Point Source, Non-Ambient)"
    source: str = "Tamil Nadu Pollution Control Board (TNPCB OCEMS)"

class OpenMeteoReading(BaseModel):
    time: str
    pm2_5: float
    pm10: float
    nitrogen_dioxide: float
    carbon_monoxide_ugm3: float
    carbon_monoxide_mgm3: float  # Converted: ug/m3 / 1000
    sulphur_dioxide: float
    ozone: float
    european_aqi: Optional[int] = None
    us_aqi: Optional[int] = None
    data_type: str = "Modelled Atmospheric Estimate"
    source: str = "Open-Meteo Air Quality Model (CAMS / SILAM / EMEP ensemble)"
    units: Dict[str, str]

class HourlyForecastPoint(BaseModel):
    time: str
    pm2_5: float
    pm10: float
    nitrogen_dioxide: float
    carbon_monoxide: float  # in mg/m3
    sulphur_dioxide: float
    ozone: float
    us_aqi: Optional[int] = None

class CityAirQualityResponse(BaseModel):
    location: LocationItem
    sources_available: List[str]
    open_meteo: Optional[OpenMeteoReading] = None
    ml_classification: Optional[Dict[str, Any]] = None
    hourly_forecast: List[HourlyForecastPoint] = []
    data_gov_in: Optional[Dict[str, Any]] = None
    tnpcb_industries: List[IndustryRecord] = []
    retrieved_at: str
    source_disclaimers: Dict[str, str]

class CityComparisonRequest(BaseModel):
    city_1: str
    city_2: str

class CityComparisonResponse(BaseModel):
    city_1: str
    city_2: str
    location_1: LocationItem
    location_2: LocationItem
    reading_1: Optional[OpenMeteoReading] = None
    reading_2: Optional[OpenMeteoReading] = None
    ml_class_1: Optional[str] = None
    ml_class_2: Optional[str] = None
    comparison_metrics: Dict[str, Dict[str, Any]]
    key_differences: List[str]
    limitations: str
