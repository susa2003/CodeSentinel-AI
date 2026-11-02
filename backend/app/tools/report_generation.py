from typing import Dict, Any, Optional, List
from backend.app.database.repository import (
    get_dataset, get_analysis_record, save_report
)
from backend.app.services.report_service import report_service
from backend.app.services.data_service import data_service

def generate_report(
    report_type: str = "pdf",
    title: str = "GreenAir Environmental Assessment Report",
    dataset_id: Optional[str] = None,
    prediction_id: Optional[str] = None,
    custom_findings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate an environmental intelligence assessment report (PDF or CSV).
    Gathers prediction records, dataset metrics, trends, and anomalies into a verifiable document.
    """
    findings = custom_findings or []
    dataset_summary = None
    prediction_data = None
    trend_data = None
    anomaly_data = None

    if dataset_id:
        dataset_summary = get_dataset(dataset_id)
        if dataset_summary:
            fn = dataset_summary.get('filename', '')
            is_synth = bool(dataset_summary.get('is_synthetic') or 'synthetic' in fn.lower())
            if is_synth:
                findings.append(f"Data source notice: '{fn}' is a SYNTHETIC DEMO dataset generated for algorithm demonstration.")
            elif dataset_summary.get("source_description"):
                findings.append(f"Data source: {dataset_summary.get('source_description')}")

            findings.append(f"Analyzed dataset '{fn}' with {dataset_summary.get('row_count')} total records.")
            findings.append(f"Data quality health index evaluated at {dataset_summary.get('data_quality_score')}/100.")
            
            # Auto-run trend and anomaly if available
            stored_path = dataset_summary.get("stored_path")
            if dataset_summary.get("has_timestamps") and stored_path:
                try:
                    trend_data = data_service.analyze_trends(stored_path, pollutant="PM2.5")
                    findings.append(f"PM2.5 time-series trend is '{trend_data['trend_direction']}' with net change of {trend_data['change_percentage']}%.")
                except Exception:
                    pass

            if stored_path:
                try:
                    anomaly_data = data_service.detect_anomalies(stored_path, pollutant="PM2.5")
                    if anomaly_data["anomaly_count"] > 0:
                        findings.append(f"Identified {anomaly_data['anomaly_count']} statistical anomaly readings in PM2.5 concentrations.")
                except Exception:
                    pass

    if prediction_id:
        record = get_analysis_record(prediction_id)
        if record and record.get("record_type") == "prediction":
            prediction_data = record.get("result", {})
            findings.append(f"Classified air quality category: '{prediction_data.get('category')}' with model confidence {prediction_data.get('confidence_pct', 0):.1f}%.")

    if not findings:
        findings.append("Automated environmental parameters review conducted with standard safety baselines.")

    if report_type.lower() == "csv" and dataset_summary:
        # Generate CSV export
        try:
            df = data_service.load_dataset_dataframe(dataset_summary["stored_path"])
            rows = df.head(1000).to_dict(orient="records")
            report_info = report_service.generate_csv_report(
                title=title,
                data_rows=rows,
                summary_metrics={"Quality Score": dataset_summary.get("data_quality_score")}
            )
        except Exception:
            report_info = report_service.generate_pdf_report(
                title=title,
                findings=findings,
                prediction_data=prediction_data,
                dataset_summary=dataset_summary,
                trend_data=trend_data,
                anomaly_data=anomaly_data
            )
    else:
        report_info = report_service.generate_pdf_report(
            title=title,
            findings=findings,
            prediction_data=prediction_data,
            dataset_summary=dataset_summary,
            trend_data=trend_data,
            anomaly_data=anomaly_data
        )

    # Save to database
    save_report(report_info)

    return report_info
