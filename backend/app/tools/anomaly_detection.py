from typing import Dict, Any, Optional
from backend.app.database.repository import get_dataset
from backend.app.services.data_service import data_service

def detect_anomalies(dataset_id: str, pollutant: str = "PM2.5", method: str = "iqr", threshold: float = 1.5) -> Dict[str, Any]:
    """
    Detect statistical outliers and unusual environmental readings within a dataset.
    Uses either the Interquartile Range (IQR) method or Robust Z-Score method.
    Identifies affected records, severity, and bounds without prematurely declaring physical sensor failures.
    """
    dataset_meta = get_dataset(dataset_id)
    if not dataset_meta:
        raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

    stored_path = dataset_meta.get("stored_path")
    result = data_service.detect_anomalies(
        stored_path=stored_path,
        pollutant=pollutant,
        method=method,
        multiplier=threshold
    )
    result["dataset_filename"] = dataset_meta.get("filename")
    return result
