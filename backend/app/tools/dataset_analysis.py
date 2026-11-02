from typing import Dict, Any, Optional
from backend.app.database.repository import get_dataset
from backend.app.services.data_service import data_service

def analyze_dataset(dataset_id: str) -> Dict[str, Any]:
    """
    Perform comprehensive data quality and environmental distribution analysis on an uploaded dataset.
    Reports row and column counts, pollutant mappings, missing value rates, duplicate rows,
    statistical summaries, and date-range coverage.
    """
    dataset_meta = get_dataset(dataset_id)
    if not dataset_meta:
        raise ValueError(f"Dataset with ID '{dataset_id}' not found in the system registry.")

    # Format descriptive statistics into a readable structured summary
    stats = dataset_meta.get("pollutant_stats", {})
    warnings = dataset_meta.get("quality_warnings", [])
    filename = dataset_meta.get("filename", "")
    is_synth = bool(dataset_meta.get("is_synthetic") or "synthetic" in filename.lower())
    source_type = dataset_meta.get("source_type") or ("synthetic_demo" if is_synth else "upload")
    source_desc = dataset_meta.get("source_description") or ("Synthetic demo data" if is_synth else "Uploaded dataset")

    provenance_note = (
        " [DATA SOURCE: SYNTHETIC DEMO - simulated illustrative data, not live measurements]"
        if is_synth
        else (
            f" [DATA SOURCE: {source_type.upper()} - {source_desc}]"
        )
    )
    
    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "source_type": source_type,
        "source_description": source_desc,
        "is_synthetic": is_synth,
        "total_records": dataset_meta.get("row_count"),
        "total_columns": dataset_meta.get("column_count"),
        "pollutant_columns_identified": dataset_meta.get("pollutant_columns", []),
        "timestamp_available": dataset_meta.get("has_timestamps", False),
        "is_time_series": dataset_meta.get("is_time_series", True),
        "date_range": {
            "start": dataset_meta.get("date_start"),
            "end": dataset_meta.get("date_end")
        },
        "missing_values_count": dataset_meta.get("missing_values_count", 0),
        "duplicate_rows_count": dataset_meta.get("duplicate_rows_count", 0),
        "data_quality_score": dataset_meta.get("data_quality_score", 0.0),
        "quality_warnings": warnings,
        "pollutant_distributions": stats,
        "summary": (
            f"Dataset '{filename}' contains {dataset_meta.get('row_count')} observations. "
            f"Data quality health score: {dataset_meta.get('data_quality_score')}/100. "
            f"Detected pollutants: {', '.join(dataset_meta.get('pollutant_columns', [])) or 'None'}."
            f"{provenance_note}"
        )
    }
