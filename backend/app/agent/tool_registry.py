import time
import json
import logging
import inspect
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Callable, Optional, Tuple

from backend.app.tools import (
    predict_air_quality,
    analyze_pollutants,
    analyze_dataset,
    analyze_trends,
    detect_anomalies,
    get_health_guidance,
    generate_report,
    compare_records,
    get_live_city_air_quality,
    get_tnpcb_industrial_emissions,
    compare_cities,
    get_cpcb_ground_observations,
)

logger = logging.getLogger(__name__)

# Registered tool handlers allowlist
ALLOWLISTED_TOOLS: Dict[str, Callable] = {
    "predict_air_quality": predict_air_quality,
    "analyze_pollutants": analyze_pollutants,
    "analyze_dataset": analyze_dataset,
    "analyze_trends": analyze_trends,
    "detect_anomalies": detect_anomalies,
    "get_health_guidance": get_health_guidance,
    "generate_report": generate_report,
    "compare_records": compare_records,
    "get_live_city_air_quality": get_live_city_air_quality,
    "get_tnpcb_industrial_emissions": get_tnpcb_industrial_emissions,
    "compare_cities": compare_cities,
    "get_cpcb_ground_observations": get_cpcb_ground_observations,
}

# OpenAI/Groq Tool Definitions Schema
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_live_city_air_quality",
            "description": "Fetch real-time atmospheric air quality data, 72-hour forecast, and ML classification for any Indian city or locality (e.g., Chennai, Delhi, Mumbai, Bengaluru, Hosur, Coimbatore).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Name of the Indian city, district, or locality (e.g. 'Chennai', 'Delhi', 'Hosur')."},
                    "force_refresh": {"type": "boolean", "description": "Whether to bypass the 15-minute cache. Default false."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cpcb_ground_observations",
            "description": "Fetch official real-time ground-level Continuous Ambient Air Quality Monitoring Station (CAAQMS) observations published by the Central Pollution Control Board (CPCB) via data.gov.in for an Indian city (e.g. Chennai, Delhi, Mumbai, Bengaluru). Provides ground station locations, pollutant parameters (PM2.5, PM10, NO2, SO2, CO, Ozone), units, and official timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Name of the Indian city (e.g. 'Chennai', 'Delhi', 'Bengaluru', 'Mumbai')."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tnpcb_industrial_emissions",
            "description": "Fetch live industrial stack emissions and effluent monitoring records from the Tamil Nadu Pollution Control Board (TNPCB OCEMS) public portal for a specific city or district in Tamil Nadu (e.g., Hosur, Chennai, Coimbatore, Thoothukudi). Explicitly note that stack emissions represent point sources and are NOT equivalent to ambient city AQI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Tamil Nadu city or district name (e.g., 'Hosur', 'Chennai', 'Coimbatore', 'Salem', 'Thoothukudi')."},
                    "emission_type": {"type": "string", "enum": ["air", "water", "all"], "description": "Filter by emission type: 'air', 'water', or 'all'. Default 'air'."},
                    "only_active": {"type": "boolean", "description": "If true, only return industries with non-zero active readings."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_cities",
            "description": "Compare real-time air quality metrics, dominant pollutant drivers, and ML classifications side by side between two Indian cities (e.g. Delhi vs Mumbai, Chennai vs Coimbatore).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_1": {"type": "string", "description": "First Indian city name (e.g., 'Delhi', 'Chennai')."},
                    "city_2": {"type": "string", "description": "Second Indian city name (e.g., 'Mumbai', 'Bengaluru')."},
                },
                "required": ["city_1", "city_2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_air_quality",
            "description": "Predict air quality category (Satisfactory, Moderate, Poor, Very Poor, Severe) using the trained GreenAir ML model for 6 pollutant concentrations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pm25": {"type": "number", "description": "PM2.5 particulate concentration in µg/m³"},
                    "pm10": {"type": "number", "description": "PM10 particulate concentration in µg/m³"},
                    "no2": {"type": "number", "description": "NO2 nitrogen dioxide concentration in µg/m³"},
                    "co": {"type": "number", "description": "CO carbon monoxide concentration in mg/m³"},
                    "so2": {"type": "number", "description": "SO2 sulfur dioxide concentration in µg/m³"},
                    "o3": {"type": "number", "description": "O3 ground-level ozone concentration in µg/m³"},
                },
                "required": ["pm25", "pm10", "no2", "co", "so2", "o3"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pollutants",
            "description": "Evaluate and rank 6 pollutant readings against normalized ambient benchmarks to determine the dominant air pollutant driver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pm25": {"type": "number", "description": "PM2.5 concentration in µg/m³"},
                    "pm10": {"type": "number", "description": "PM10 concentration in µg/m³"},
                    "no2": {"type": "number", "description": "NO2 concentration in µg/m³"},
                    "co": {"type": "number", "description": "CO concentration in mg/m³"},
                    "so2": {"type": "number", "description": "SO2 concentration in µg/m³"},
                    "o3": {"type": "number", "description": "O3 concentration in µg/m³"},
                },
                "required": ["pm25", "pm10", "no2", "co", "so2", "o3"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_dataset",
            "description": "Audit and compute descriptive distributions, quality metrics, and missing values for an uploaded dataset ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "The unique identifier of the uploaded dataset."},
                },
                "required": ["dataset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_trends",
            "description": "Calculate time-series trends, slope, percent change, and rolling averages for a pollutant in an uploaded dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "The dataset ID with chronological timestamp records."},
                    "pollutant": {"type": "string", "description": "Target pollutant (e.g., 'PM2.5', 'PM10', 'NO2', 'CO', 'SO2', 'O3'). Default 'PM2.5'."},
                    "rolling_window": {"type": "integer", "description": "Moving average window size. Default 3."},
                },
                "required": ["dataset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "Identify statistical outliers and anomalies in a dataset using the IQR or Robust Z-Score method.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "The dataset ID to scan for outliers."},
                    "pollutant": {"type": "string", "description": "Pollutant column to analyze. Default 'PM2.5'."},
                    "method": {"type": "string", "enum": ["iqr", "zscore"], "description": "Outlier detection method: 'iqr' or 'zscore'. Default 'iqr'."},
                    "threshold": {"type": "number", "description": "Multiplier threshold (e.g., 1.5 for IQR or 3.0 for Z-Score). Default 1.5."},
                },
                "required": ["dataset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_health_guidance",
            "description": "Obtain evidence-based health guidance and precautions for an air quality category and sensitive populations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Air quality category: 'Satisfactory', 'Moderate', 'Poor', 'Very Poor', or 'Severe'."},
                    "dominant_pollutant": {"type": "string", "description": "Optional dominant pollutant driving the advisory (e.g., 'PM2.5', 'O3')."},
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Compile verified predictions, dataset statistics, and findings into a downloadable PDF or CSV report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {"type": "string", "enum": ["pdf", "csv"], "description": "Report output format: 'pdf' or 'csv'."},
                    "title": {"type": "string", "description": "Title of the assessment report."},
                    "dataset_id": {"type": "string", "description": "Optional dataset ID to incorporate."},
                    "prediction_id": {"type": "string", "description": "Optional prediction record ID to include."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_records",
            "description": "Compare two uploaded datasets or prediction records side by side to assess changes in air quality parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_ids": {"type": "array", "items": {"type": "string"}, "description": "List of 2 dataset IDs to compare."},
                    "prediction_ids": {"type": "array", "items": {"type": "string"}, "description": "List of 2 prediction IDs to compare."},
                },
            },
        },
    },
]

def _sanitize_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize arguments by parsing numeric strings to floats/ints where appropriate."""
    clean_args = {}
    for k, v in arguments.items():
        if isinstance(v, str):
            try:
                if "." in v:
                    clean_args[k] = float(v)
                else:
                    clean_args[k] = int(v)
            except ValueError:
                clean_args[k] = v
        else:
            clean_args[k] = v
    return clean_args

async def execute_tool_async(tool_name: str, arguments: Dict[str, Any]) -> Tuple[Any, float, bool, Optional[str]]:
    """
    Safely execute an allowlisted tool function asynchronously.
    Supports both sync and async tool handlers.
    Returns (output, execution_time_ms, success_bool, error_string).
    """
    if tool_name not in ALLOWLISTED_TOOLS:
        error_msg = f"Security Error: Tool '{tool_name}' is not in the allowlisted tool registry."
        logger.warning(error_msg)
        return None, 0.0, False, error_msg

    handler = ALLOWLISTED_TOOLS[tool_name]
    t0 = time.time()
    try:
        clean_args = _sanitize_arguments(arguments)
        if inspect.iscoroutinefunction(handler):
            output = await handler(**clean_args)
        else:
            output = handler(**clean_args)
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return output, elapsed_ms, True, None
    except Exception as exc:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        error_msg = f"Tool execution failed: {str(exc)}"
        logger.error(f"Error in tool '{tool_name}': {exc}", exc_info=True)
        return None, elapsed_ms, False, error_msg

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Tuple[Any, float, bool, Optional[str]]:
    """
    Synchronous wrapper to safely execute an allowlisted tool.
    Handles sync tools directly, and runs async tools in an isolated thread worker.
    Returns (output, execution_time_ms, success_bool, error_string).
    """
    if tool_name not in ALLOWLISTED_TOOLS:
        error_msg = f"Security Error: Tool '{tool_name}' is not in the allowlisted tool registry."
        logger.warning(error_msg)
        return None, 0.0, False, error_msg

    handler = ALLOWLISTED_TOOLS[tool_name]
    t0 = time.time()
    try:
        clean_args = _sanitize_arguments(arguments)
        if inspect.iscoroutinefunction(handler):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                output = executor.submit(asyncio.run, handler(**clean_args)).result()
        else:
            output = handler(**clean_args)
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return output, elapsed_ms, True, None
    except Exception as exc:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        error_msg = f"Tool execution failed: {str(exc)}"
        logger.error(f"Error in tool '{tool_name}': {exc}", exc_info=True)
        return None, elapsed_ms, False, error_msg
