from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.app.config import settings
from backend.app.schemas.schemas import DatasetSummary
from backend.app.services.data_service import data_service
from backend.app.services.datagov_service import datagov_service
from backend.app.services.open_meteo_service import open_meteo_service
from backend.app.services.location_service import location_service
from backend.app.database.repository import (
    save_dataset, get_dataset, list_datasets
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(file: UploadFile = File(...)):
    """Upload and audit a CSV or Excel environmental air quality dataset."""
    filename = file.filename or "uploaded_data.csv"
    ext = Path(filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Read bytes with file size limit check
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    try:
        summary = data_service.process_uploaded_file(contents, filename)
        save_dataset(summary)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process dataset: {str(exc)}")

@router.post("/import/cpcb", response_model=DatasetSummary)
async def import_cpcb_dataset(
    city: str = Query(default="Chennai", description="Indian city name (e.g. Chennai, Delhi, Bengaluru)"),
    limit: int = Query(default=200, ge=10, le=500, description="Max observations to query")
):
    """
    Import official ground Continuous Ambient Air Quality Monitoring Station (CAAQMS)
    observations for a city from CPCB via data.gov.in as an Active Dataset.
    Preserves exact station names, coordinates, observation timestamps, and unmeasured parameters.
    """
    try:
        summary = await datagov_service.import_city_as_dataset(city=city, limit=limit)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to import CPCB dataset for {city}: {str(exc)}")

@router.post("/import/open-meteo", response_model=DatasetSummary)
async def import_open_meteo_dataset(
    city: str = Query(default="Chennai", description="Indian city name"),
    latitude: Optional[float] = Query(default=None, description="Optional exact latitude"),
    longitude: Optional[float] = Query(default=None, description="Optional exact longitude")
):
    """
    Import 72-hour hourly numerical model air quality time series (CAMS/SILAM ensemble)
    from Open-Meteo as an Active Dataset for chronological trend analysis and anomaly detection.
    """
    try:
        lat = latitude
        lon = longitude
        if lat is None or lon is None:
            locs = await location_service.search_indian_locations(city)
            if not locs:
                raise ValueError(f"Could not resolve geographic coordinates for city '{city}'.")
            lat = locs[0]["latitude"]
            lon = locs[0]["longitude"]

        summary = await open_meteo_service.import_city_as_dataset(city=city, latitude=lat, longitude=lon)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to import Open-Meteo series for {city}: {str(exc)}")

@router.post("/{dataset_id}/activate", response_model=DatasetSummary)
def activate_dataset(dataset_id: str):
    """Explicitly activate a dataset by ID."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset with ID '{dataset_id}' not found.")
    return ds

@router.get("", response_model=List[DatasetSummary])
def get_datasets():
    """List all registered environmental datasets."""
    datasets = list_datasets()
    return datasets

@router.get("/{dataset_id}", response_model=DatasetSummary)
def get_dataset_details(dataset_id: str):
    """Retrieve full summary and distributions for a specific dataset."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset with ID '{dataset_id}' not found.")
    return ds

@router.get("/{dataset_id}/summary", response_model=DatasetSummary)
def get_dataset_summary(dataset_id: str):
    """Alias for dataset summary."""
    return get_dataset_details(dataset_id)
