import os
import io
import re
import math
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from backend.app.config import settings

# Canonical pollutant name mappings
POLLUTANT_PATTERNS = {
    "PM2.5": [r"^pm2\.?5$", r"^pm_?25$", r"^pm25_", r"^particulate_?2\.?5$"],
    "PM10": [r"^pm10$", r"^pm_?10$", r"^particulate_?10$"],
    "NO2": [r"^no2$", r"^nitrogen_?dioxide$", r"^no_2$"],
    "CO": [r"^co$", r"^carbon_?monoxide$"],
    "SO2": [r"^so2$", r"^sulfur_?dioxide$", r"^so_2$"],
    "O3": [r"^o3$", r"^ozone$", r"^o_3$"],
}

TIMESTAMP_PATTERNS = [
    r"^timestamp$", r"^datetime$", r"^date_?time$", r"^date$", r"^time$",
    r"^recorded_?at$", r"^sample_?time$", r"^reading_?time$"
]

class DataService:
    @staticmethod
    def map_columns(df: pd.DataFrame) -> Tuple[Dict[str, str], Optional[str]]:
        """Identify pollutant columns and timestamp column using conservative regex matching."""
        column_map = {}
        timestamp_col = None

        for col in df.columns:
            clean_col = str(col).strip().lower()
            clean_col = re.sub(r"[()\[\]/\\_\s]+", "_", clean_col).strip("_")

            # Check timestamp first
            if not timestamp_col:
                for tp in TIMESTAMP_PATTERNS:
                    if re.match(tp, clean_col):
                        timestamp_col = str(col)
                        break

            # Check pollutants
            for canonical, patterns in POLLUTANT_PATTERNS.items():
                if canonical not in column_map.values():
                    for pattern in patterns:
                        if re.match(pattern, clean_col):
                            column_map[str(col)] = canonical
                            break

        return column_map, timestamp_col

    @classmethod
    def process_uploaded_file(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate, store, parse, and analyze an uploaded dataset."""
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {', '.join(settings.ALLOWED_EXTENSIONS)}")

        # Read into DataFrame
        try:
            if ext == ".csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Could not parse file '{filename}': {str(e)}")

        if df.empty:
            raise ValueError("Uploaded file contains no data (empty table).")

        row_count, col_count = df.shape
        if row_count > 100000:
            df = df.iloc[:100000]  # Cap for safety in MVP

        # Identify columns
        col_map, timestamp_col = cls.map_columns(df)
        pollutant_cols = list(col_map.values())

        quality_warnings = []

        # Check timestamps
        has_timestamps = False
        is_time_series = False
        date_start = None
        date_end = None

        if timestamp_col:
            try:
                # Try parsing timestamp
                parsed_dates = pd.to_datetime(df[timestamp_col], errors="coerce", dayfirst=True)
                valid_dates = parsed_dates.dropna()
                if len(valid_dates) >= len(df) * 0.5:
                    has_timestamps = True
                    df["_parsed_timestamp"] = parsed_dates
                    date_start = valid_dates.min().isoformat()
                    date_end = valid_dates.max().isoformat()
                    if valid_dates.nunique() > 1:
                        is_time_series = True
                    else:
                        is_time_series = False
                        quality_warnings.append(
                            "Dataset contains spatial observations recorded at a single timestamp snapshot. "
                            "Time-series trend slopes require multiple distinct chronological timestamps."
                        )
            except Exception:
                has_timestamps = False

        # Compute data quality metrics
        missing_count = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())

        if not pollutant_cols:
            quality_warnings.append("No recognizable air quality pollutant columns found (PM2.5, PM10, NO2, CO, SO2, O3).")
        else:
            missing_pollutants = [p for p in ["PM2.5", "PM10", "NO2", "CO", "SO2", "O3"] if p not in pollutant_cols]
            if missing_pollutants:
                quality_warnings.append(f"Missing pollutant columns for full 6-feature classification: {', '.join(missing_pollutants)}")

        if missing_count > 0:
            quality_warnings.append(f"Detected {missing_count} missing cell(s) across the dataset.")

        if duplicate_count > 0:
            quality_warnings.append(f"Found {duplicate_count} duplicate row(s) in the dataset.")

        if not has_timestamps:
            quality_warnings.append("No valid timestamp column identified. Time-series trend analysis will be unavailable.")

        # Data quality score: max 100
        # Penalize for missing cells, duplicates, missing pollutant columns
        penalty = 0
        total_cells = max(row_count * col_count, 1)
        missing_pct = (missing_count / total_cells) * 100
        dup_pct = (duplicate_count / max(row_count, 1)) * 100

        penalty += min(missing_pct * 2, 30)
        penalty += min(dup_pct * 2, 20)
        if len(pollutant_cols) < 3:
            penalty += 25
        elif len(pollutant_cols) < 6:
            penalty += 10
        if not has_timestamps:
            penalty += 15

        data_quality_score = max(0.0, min(100.0, round(100.0 - penalty, 1)))

        # Compute descriptive statistics for mapped pollutant columns
        stats_dict = {}
        for original_col, canonical in col_map.items():
            numeric_series = pd.to_numeric(df[original_col], errors="coerce").dropna()
            if not numeric_series.empty:
                stats_dict[canonical] = {
                    "count": float(len(numeric_series)),
                    "mean": round(float(numeric_series.mean()), 2),
                    "std": round(float(numeric_series.std()), 2) if len(numeric_series) > 1 else 0.0,
                    "min": round(float(numeric_series.min()), 2),
                    "q25": round(float(numeric_series.quantile(0.25)), 2),
                    "median": round(float(numeric_series.median()), 2),
                    "q75": round(float(numeric_series.quantile(0.75)), 2),
                    "max": round(float(numeric_series.max()), 2),
                }

        # Save to disk
        dataset_id = str(uuid.uuid4())
        safe_filename = f"{dataset_id}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)}"
        file_path = settings.UPLOAD_DIR / safe_filename
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Preview rows (convert NaN to None for JSON serialization)
        preview_df = df.head(10).copy()
        if "_parsed_timestamp" in preview_df.columns:
            preview_df.drop(columns=["_parsed_timestamp"], inplace=True)
        preview_records = preview_df.replace({np.nan: None}).to_dict(orient="records")

        # Infer source metadata
        is_synthetic = "synthetic" in filename.lower()
        if is_synthetic:
            source_type = "synthetic_demo"
            source_description = "Synthetic demonstration dataset with simulated pollutant trajectories."
        else:
            source_type = "upload"
            source_description = "User-uploaded environmental dataset."

        summary = {
            "id": dataset_id,
            "filename": filename,
            "stored_path": str(file_path),
            "row_count": row_count,
            "column_count": col_count,
            "columns": [str(c) for c in df.columns if c != "_parsed_timestamp"],
            "pollutant_columns": pollutant_cols,
            "column_mappings": col_map,
            "has_timestamps": has_timestamps,
            "timestamp_column": timestamp_col,
            "date_start": date_start,
            "date_end": date_end,
            "missing_values_count": missing_count,
            "duplicate_rows_count": duplicate_count,
            "data_quality_score": data_quality_score,
            "quality_warnings": quality_warnings,
            "pollutant_stats": stats_dict,
            "preview_rows": preview_records,
            "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "source_type": source_type,
            "source_description": source_description,
            "is_synthetic": is_synthetic,
            "is_time_series": is_time_series,
        }

        return summary

    @classmethod
    def load_dataset_dataframe(cls, stored_path: str) -> pd.DataFrame:
        """Load stored dataset from disk safely."""
        path = Path(stored_path)
        if not path.is_file():
            raise FileNotFoundError(f"Dataset file not found at: {stored_path}")
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        return df

    @classmethod
    def analyze_trends(cls, stored_path: str, pollutant: str = "PM2.5", rolling_window: int = 3) -> Dict[str, Any]:
        """Compute time series trends with statistical slope, percentage change, and moving averages."""
        df = cls.load_dataset_dataframe(stored_path)
        col_map, timestamp_col = cls.map_columns(df)

        if not timestamp_col:
            raise ValueError("Trend analysis requires a dataset with a valid timestamp or date column.")

        # Find target column
        target_col = None
        for orig, canon in col_map.items():
            if canon.upper() == pollutant.upper():
                target_col = orig
                break

        if not target_col:
            # Check if column name directly matches
            for col in df.columns:
                if col.upper() == pollutant.upper():
                    target_col = col
                    break

        if not target_col:
            raise ValueError(f"Pollutant '{pollutant}' not found in the dataset.")

        # Parse and sort by timestamp
        df_clean = df[[timestamp_col, target_col]].copy()
        df_clean["_time"] = pd.to_datetime(df_clean[timestamp_col], errors="coerce", dayfirst=True)
        df_clean["_val"] = pd.to_numeric(df_clean[target_col], errors="coerce")
        df_clean = df_clean.dropna().sort_values("_time")

        if len(df_clean) < 3:
            raise ValueError(f"Insufficient valid data points ({len(df_clean)}) to compute trends. Minimum 3 required.")

        if df_clean["_time"].nunique() < 2:
            raise ValueError(
                f"The active dataset contains spatial observations from a single observation time snapshot ({df_clean['_time'].iloc[0]}). "
                "Time-series trend analysis requires observations across multiple distinct chronological timestamps. "
                "To analyze multi-day/hourly time-series trends, please import or select a time-series dataset (such as an Open-Meteo 72-hour forecast dataset or the synthetic demo dataset)."
            )

        # Cap points for charts if large (sample uniformly)
        if len(df_clean) > 200:
            step = len(df_clean) // 100
            plot_df = df_clean.iloc[::step].copy()
        else:
            plot_df = df_clean.copy()

        # Compute rolling average
        plot_df["_rolling"] = plot_df["_val"].rolling(window=max(1, rolling_window), min_periods=1).mean()

        data_points = []
        for _, row in plot_df.iterrows():
            data_points.append({
                "timestamp": str(row["_time"]),
                "value": round(float(row["_val"]), 2),
                "rolling_avg": round(float(row["_rolling"]), 2)
            })

        # Calculate slope via linear regression
        x = np.arange(len(df_clean))
        y = df_clean["_val"].values
        slope, intercept = np.polyfit(x, y, 1)

        init_val = float(df_clean["_val"].iloc[0])
        final_val = float(df_clean["_val"].iloc[-1])
        change_pct = round(((final_val - init_val) / max(abs(init_val), 0.001)) * 100, 2)

        # Trend direction
        if abs(slope) < 0.05 and abs(change_pct) < 5.0:
            direction = "Stable"
        elif slope > 0:
            direction = "Increasing"
        else:
            direction = "Decreasing"

        return {
            "pollutant": pollutant,
            "trend_direction": direction,
            "slope": round(float(slope), 4),
            "change_percentage": change_pct,
            "initial_value": round(init_val, 2),
            "final_value": round(final_val, 2),
            "min_value": round(float(df_clean["_val"].min()), 2),
            "max_value": round(float(df_clean["_val"].max()), 2),
            "mean_value": round(float(df_clean["_val"].mean()), 2),
            "point_count": len(df_clean),
            "coverage_note": f"Analyzed {len(df_clean)} chronological observations from {df_clean['_time'].min()} to {df_clean['_time'].max()}.",
            "data_points": data_points
        }

    @classmethod
    def detect_anomalies(cls, stored_path: str, pollutant: str = "PM2.5", method: str = "iqr", multiplier: float = 1.5) -> Dict[str, Any]:
        """Detect statistical anomalies using IQR or Robust Z-score."""
        df = cls.load_dataset_dataframe(stored_path)
        col_map, timestamp_col = cls.map_columns(df)

        target_col = None
        for orig, canon in col_map.items():
            if canon.upper() == pollutant.upper():
                target_col = orig
                break
        if not target_col:
            for col in df.columns:
                if col.upper() == pollutant.upper():
                    target_col = col
                    break

        if not target_col:
            raise ValueError(f"Pollutant '{pollutant}' not found in the dataset.")

        series = pd.to_numeric(df[target_col], errors="coerce").dropna()
        if len(series) < 5:
            raise ValueError("At least 5 valid observations are required for anomaly detection.")

        anomalies = []
        total_count = len(series)

        if method.lower() == "zscore":
            mean = series.mean()
            std = series.std() if len(series) > 1 else 1.0
            z_thresh = multiplier if multiplier > 0 else 3.0
            lower_bound = round(float(mean - z_thresh * std), 2)
            upper_bound = round(float(mean + z_thresh * std), 2)

            for idx, val in series.items():
                z = (val - mean) / (std if std != 0 else 1.0)
                if abs(z) >= z_thresh:
                    ts = str(df.loc[idx, timestamp_col]) if timestamp_col and timestamp_col in df.columns else None
                    severity = "High" if abs(z) >= (z_thresh * 1.5) else ("Moderate" if abs(z) >= z_thresh else "Low")
                    anomalies.append({
                        "row_index": int(idx),
                        "timestamp": ts,
                        "pollutant": pollutant,
                        "value": round(float(val), 2),
                        "threshold_low": lower_bound,
                        "threshold_high": upper_bound,
                        "score": round(float(z), 2),
                        "severity": severity,
                        "explanation": f"Statistical outlier with Z-score {z:.2f} exceeding threshold of ±{z_thresh} standard deviations."
                    })
        else:
            # Default IQR method
            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25
            mult = multiplier if multiplier > 0 else 1.5
            lower_bound = round(float(q25 - mult * iqr), 2)
            upper_bound = round(float(q75 + mult * iqr), 2)

            for idx, val in series.items():
                if val < lower_bound or val > upper_bound:
                    dist = (val - upper_bound) if val > upper_bound else (lower_bound - val)
                    score = dist / (iqr if iqr != 0 else 1.0)
                    ts = str(df.loc[idx, timestamp_col]) if timestamp_col and timestamp_col in df.columns else None
                    severity = "High" if score >= 2.0 else "Moderate"
                    anomalies.append({
                        "row_index": int(idx),
                        "timestamp": ts,
                        "pollutant": pollutant,
                        "value": round(float(val), 2),
                        "threshold_low": lower_bound,
                        "threshold_high": upper_bound,
                        "score": round(float(score), 2),
                        "severity": severity,
                        "explanation": f"Value {val:.1f} lies beyond IQR bounds [{lower_bound}, {upper_bound}]."
                    })

        anomaly_count = len(anomalies)
        anomaly_pct = round((anomaly_count / max(total_count, 1)) * 100, 2)

        return {
            "dataset_id": Path(stored_path).stem.split("_")[0],
            "pollutant": pollutant,
            "method": method.upper(),
            "total_records_examined": total_count,
            "anomaly_count": anomaly_count,
            "anomaly_percentage": anomaly_pct,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "anomalies": anomalies[:50],  # Return up to 50 for clean reporting
            "interpretation_note": (
                "Important: Statistical anomalies indicate values that deviate significantly from the sample distribution. "
                "They should not be automatically assumed to be sensor failures or confirmed environmental emergencies "
                "without ground-truth validation."
            )
        }

data_service = DataService()
