from typing import Dict, Any, Optional
from backend.app.database.repository import get_dataset
from backend.app.services.data_service import data_service

def analyze_trends(dataset_id: str, pollutant: str = "PM2.5", rolling_window: int = 3) -> Dict[str, Any]:
    """
    Analyze historical time-series pollutant trends.
    Requires that the dataset possesses valid chronological timestamp records.
    Computes slope, net percentage change, min/max/mean bounds, and moving average trajectories.
    """
    dataset_meta = get_dataset(dataset_id)
    if not dataset_meta:
        raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

    if not dataset_meta.get("has_timestamps"):
        raise ValueError(
            f"Dataset '{dataset_meta.get('filename')}' does not contain recognized timestamp records. "
            "Historical time-series trend analysis cannot be performed without chronological time data."
        )

    stored_path = dataset_meta.get("stored_path")
    result = data_service.analyze_trends(
        stored_path=stored_path,
        pollutant=pollutant,
        rolling_window=rolling_window
    )
    filename = dataset_meta.get("filename", "")
    is_synth = bool(dataset_meta.get("is_synthetic") or "synthetic" in filename.lower())
    result["dataset_filename"] = filename
    result["is_synthetic"] = is_synth
    result["source_type"] = dataset_meta.get("source_type") or ("synthetic_demo" if is_synth else "upload")
    result["source_description"] = dataset_meta.get("source_description")
    if is_synth:
        result["data_source_notice"] = "Notice: This trend analysis is based on a SYNTHETIC DEMO dataset generated for algorithm demonstration."
    else:
        result["data_source_notice"] = f"Data source: {dataset_meta.get('source_description') or filename}"
    return result
