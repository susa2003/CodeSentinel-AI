from typing import Dict, Any, List, Optional
from backend.app.database.repository import get_dataset, get_analysis_record

def compare_records(
    dataset_ids: Optional[List[str]] = None,
    prediction_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compare multiple datasets or prediction records side by side.
    Evaluates changes in pollutant distributions, categories, and data quality across monitoring periods.
    """
    if not dataset_ids and not prediction_ids:
        raise ValueError("Must provide at least one pair of dataset_ids or prediction_ids to compare.")

    key_differences = []
    metrics_comparison = {}
    compared_entities = []

    if dataset_ids and len(dataset_ids) >= 2:
        d1 = get_dataset(dataset_ids[0])
        d2 = get_dataset(dataset_ids[1])
        if not d1 or not d2:
            raise ValueError("One or both dataset IDs could not be located in registry.")

        compared_entities = [d1.get("filename", "Dataset 1"), d2.get("filename", "Dataset 2")]
        metrics_comparison["records_count"] = {d1["filename"]: d1["row_count"], d2["filename"]: d2["row_count"]}
        metrics_comparison["quality_score"] = {d1["filename"]: d1["data_quality_score"], d2["filename"]: d2["data_quality_score"]}

        # Compare common pollutants
        s1 = d1.get("pollutant_stats", {})
        s2 = d2.get("pollutant_stats", {})
        common_pollutants = set(s1.keys()).intersection(set(s2.keys()))

        for p in common_pollutants:
            m1 = s1[p].get("mean", 0.0)
            m2 = s2[p].get("mean", 0.0)
            diff = round(m2 - m1, 2)
            pct = round((diff / max(m1, 0.01)) * 100, 1)
            metrics_comparison[f"{p}_mean"] = {d1["filename"]: m1, d2["filename"]: m2, "diff": diff, "pct_change": pct}
            if abs(pct) >= 10.0:
                direction = "higher" if diff > 0 else "lower"
                key_differences.append(f"{p} average is {abs(pct)}% {direction} in {d2['filename']} ({m2}) compared to {d1['filename']} ({m1}).")

        if not key_differences:
            key_differences.append("Pollutant averages remained comparable within a ±10% margin across both datasets.")

        comp_type = "Dataset Comparison"

    elif prediction_ids and len(prediction_ids) >= 2:
        r1 = get_analysis_record(prediction_ids[0])
        r2 = get_analysis_record(prediction_ids[1])
        if not r1 or not r2:
            raise ValueError("One or both prediction IDs could not be found.")

        res1 = r1.get("result", {})
        res2 = r2.get("result", {})
        compared_entities = [f"Prediction 1 ({res1.get('category')})", f"Prediction 2 ({res2.get('category')})"]

        metrics_comparison["category"] = {"P1": res1.get("category"), "P2": res2.get("category")}
        metrics_comparison["confidence"] = {"P1": res1.get("confidence_pct"), "P2": res2.get("confidence_pct")}

        inputs1 = res1.get("input_values", {})
        inputs2 = res2.get("input_values", {})
        for p in inputs1:
            if p in inputs2:
                metrics_comparison[p] = {"P1": inputs1[p], "P2": inputs2[p]}
                if inputs1[p] != inputs2[p]:
                    key_differences.append(f"{p} shifted from {inputs1[p]} to {inputs2[p]}.")

        comp_type = "Prediction Comparison"
    else:
        raise ValueError("At least 2 records are required for a meaningful comparison.")

    return {
        "comparison_type": comp_type,
        "compared_entities": compared_entities,
        "metrics_comparison": metrics_comparison,
        "key_differences": key_differences,
        "limitations": "Ensure compared records share identical measuring units and compatible temporal sampling windows."
    }
