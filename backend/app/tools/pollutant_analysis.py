from typing import Dict, Any, Union, List

# Authoritative standard ambient benchmarks (24-hour / 8-hour exposure standards)
# Note: Units differ (CO is in mg/m³, others in µg/m³)
STANDARDS = {
    "PM2.5": {
        "benchmark": 60.0,
        "unit": "µg/m³",
        "source": "Ambient Standard Benchmark (24-hr)",
        "description": "Fine inhalable particles ≤2.5 micrometers. Deep lung penetration risk."
    },
    "PM10": {
        "benchmark": 100.0,
        "unit": "µg/m³",
        "source": "Ambient Standard Benchmark (24-hr)",
        "description": "Coarse particulate matter ≤10 micrometers (dust, pollen, mold)."
    },
    "NO2": {
        "benchmark": 80.0,
        "unit": "µg/m³",
        "source": "Ambient Standard Benchmark (24-hr)",
        "description": "Nitrogen dioxide from vehicular combustion and high-temp industrial processes."
    },
    "CO": {
        "benchmark": 2.0,
        "unit": "mg/m³",
        "source": "Ambient Standard Benchmark (8-hr)",
        "description": "Carbon monoxide from incomplete combustion. Reduces blood oxygen carrying capacity."
    },
    "SO2": {
        "benchmark": 80.0,
        "unit": "µg/m³",
        "source": "Ambient Standard Benchmark (24-hr)",
        "description": "Sulfur dioxide from coal/fuel oil burning and smelters. Potent bronchoconstrictor."
    },
    "O3": {
        "benchmark": 100.0,
        "unit": "µg/m³",
        "source": "Ambient Standard Benchmark (8-hr)",
        "description": "Photochemical ground-level ozone. Respiratory irritant formed via NOx and VOCs."
    }
}

def analyze_pollutants(
    pm25: Union[float, int],
    pm10: Union[float, int],
    no2: Union[float, int],
    co: Union[float, int],
    so2: Union[float, int],
    o3: Union[float, int],
) -> Dict[str, Any]:
    """
    Perform multi-pollutant comparative analysis using normalized benchmark ratios.
    Does not falsely equate different units or uncalibrated raw values.
    Identifies dominant pollutants and highlights parameters requiring heightened attention.
    """
    readings = {
        "PM2.5": float(pm25),
        "PM10": float(pm10),
        "NO2": float(no2),
        "CO": float(co),
        "SO2": float(so2),
        "O3": float(o3),
    }

    metrics = []
    attention_flags = []
    highest_ratio = -1.0
    dominant_pollutant = "None"

    for name, val in readings.items():
        spec = STANDARDS[name]
        ratio = round(val / spec["benchmark"], 2)
        
        if ratio >= 1.5:
            status = "Elevated Hazard"
            attention_flags.append(f"{name} is at {val:.1f} {spec['unit']} ({ratio}x the {spec['benchmark']} {spec['unit']} benchmark). Heightened exposure concern.")
        elif ratio >= 1.0:
            status = "Exceeds Benchmark"
            attention_flags.append(f"{name} ({val:.1f} {spec['unit']}) exceeds the standard threshold of {spec['benchmark']} {spec['unit']}.")
        elif ratio >= 0.7:
            status = "Moderate / Near Benchmark"
        else:
            status = "Within Safe Baseline"

        if ratio > highest_ratio:
            highest_ratio = ratio
            dominant_pollutant = name

        metrics.append({
            "pollutant": name,
            "value": round(val, 2),
            "unit": spec["unit"],
            "standard_benchmark": spec["benchmark"],
            "benchmark_ratio": ratio,
            "benchmark_source": spec["source"],
            "status": status,
            "description": spec["description"]
        })

    # Sort metrics by normalized benchmark ratio descending
    metrics.sort(key=lambda x: x["benchmark_ratio"], reverse=True)

    summary_text = (
        f"Multi-pollutant analysis identified **{dominant_pollutant}** as the primary driver of ambient air degradation, "
        f"reaching {highest_ratio}x its standard environmental threshold. "
    )
    if attention_flags:
        summary_text += f"{len(attention_flags)} pollutant parameter(s) currently meet or exceed recognized health benchmarks."
    else:
        summary_text += "All evaluated pollutants currently remain within their respective baseline environmental thresholds."

    scientific_context = (
        "Scientific Context: Raw concentrations of disparate pollutants (e.g., CO in mg/m³ versus PM2.5 in µg/m³) "
        "cannot be compared directly by magnitude. Instead, GreenAir computes dimensionless benchmark ratios "
        "(measured concentration divided by established exposure threshold) to provide scientifically valid comparisons."
    )

    return {
        "dominant_pollutant": dominant_pollutant,
        "highest_relative_pollutant": dominant_pollutant,
        "highest_benchmark_ratio": highest_ratio,
        "metrics": metrics,
        "attention_flags": attention_flags,
        "summary_text": summary_text,
        "scientific_context": scientific_context
    }
