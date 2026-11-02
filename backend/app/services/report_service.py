import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

from backend.app.config import settings

class ReportService:
    @classmethod
    def generate_pdf_report(
        cls,
        title: str,
        findings: List[str],
        prediction_data: Optional[Dict[str, Any]] = None,
        dataset_summary: Optional[Dict[str, Any]] = None,
        trend_data: Optional[Dict[str, Any]] = None,
        anomaly_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a branded GreenAir environmental intelligence PDF report."""
        report_id = str(uuid.uuid4())
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"GreenAir_Report_{safe_title}_{timestamp_str}_{report_id[:8]}.pdf"
        file_path = settings.REPORTS_DIR / filename

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        
        # Custom palette: Forest green & charcoal
        c_forest = colors.HexColor("#064e3b")
        c_emerald = colors.HexColor("#059669")
        c_charcoal = colors.HexColor("#1f2937")
        c_muted = colors.HexColor("#4b5563")
        c_bg_light = colors.HexColor("#f0fdf4")
        c_border = colors.HexColor("#d1fae5")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=c_forest,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=c_muted,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=c_forest,
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=c_charcoal,
        )
        callout_style = ParagraphStyle(
            "Callout",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#065f46"),
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=c_muted,
        )

        elements = []

        # Header banner
        now_readable = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        elements.append(Paragraph("🌿 GREENAIR ENVIRONMENTAL INTELLIGENCE", subtitle_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(f"Document ID: {report_id}  |  Generated: {now_readable}", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=c_emerald, spaceBefore=4, spaceAfter=14))

        # Executive Summary / Findings
        elements.append(Paragraph("1. Executive Summary & Findings", h2_style))
        if findings:
            for f in findings:
                elements.append(Paragraph(f"• {f}", body_style))
                elements.append(Spacer(1, 3))
        else:
            elements.append(Paragraph("No critical environmental anomalies or adverse thresholds identified.", body_style))
        elements.append(Spacer(1, 10))

        # Prediction Section
        if prediction_data:
            elements.append(Paragraph("2. Air Quality Classification & Model Output", h2_style))
            cat = prediction_data.get("category", "Unknown")
            conf = prediction_data.get("confidence_pct", 0.0)
            model_name = prediction_data.get("model_name", "RandomForestClassifier")
            guidance = prediction_data.get("health_guidance", "Follow local air quality advisories.")

            pred_table_data = [
                [Paragraph("<b>Classified Category:</b>", body_style), Paragraph(f"<b>{cat}</b>", body_style)],
                [Paragraph("<b>Model Confidence:</b>", body_style), Paragraph(f"{conf:.2f}%", body_style)],
                [Paragraph("<b>Model Reference:</b>", body_style), Paragraph(str(model_name), body_style)],
                [Paragraph("<b>Actionable Guidance:</b>", body_style), Paragraph(str(guidance), body_style)],
            ]

            t_pred = Table(pred_table_data, colWidths=[1.8 * inch, 4.5 * inch])
            t_pred.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
                ("BOX", (0, 0), (-1, -1), 1, c_border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(t_pred)
            elements.append(Spacer(1, 8))

            # Input pollutant values table
            inputs = prediction_data.get("input_values", {})
            if inputs:
                elements.append(Paragraph("<b>Input Pollutant Concentrations:</b>", body_style))
                elements.append(Spacer(1, 4))
                p_rows = [["Pollutant", "Measured Concentration", "Reference Benchmark", "Status"]]
                benchmarks = {"PM2.5": "60 µg/m³", "PM10": "100 µg/m³", "NO2": "80 µg/m³", "CO": "2.0 mg/m³", "SO2": "80 µg/m³", "O3": "100 µg/m³"}
                for k, v in inputs.items():
                    bm = benchmarks.get(k, "N/A")
                    p_rows.append([k, f"{v:.2f}", bm, "Monitored"])
                t_inputs = Table(p_rows, colWidths=[1.5 * inch, 1.8 * inch, 1.8 * inch, 1.2 * inch])
                t_inputs.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), c_forest),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ]))
                elements.append(t_inputs)
                elements.append(Spacer(1, 10))

        # Dataset Section
        if dataset_summary:
            elements.append(Paragraph("3. Dataset Quality & Descriptive Statistics", h2_style))
            d_rows = [
                [Paragraph("<b>Filename:</b>", body_style), Paragraph(str(dataset_summary.get("filename")), body_style)],
                [Paragraph("<b>Observations:</b>", body_style), Paragraph(f"{dataset_summary.get('row_count')} records ({dataset_summary.get('column_count')} columns)", body_style)],
                [Paragraph("<b>Data Quality Score:</b>", body_style), Paragraph(f"{dataset_summary.get('data_quality_score')}/100", body_style)],
                [Paragraph("<b>Date Span:</b>", body_style), Paragraph(f"{dataset_summary.get('date_start', 'N/A')} to {dataset_summary.get('date_end', 'N/A')}", body_style)],
            ]
            t_data = Table(d_rows, colWidths=[1.8 * inch, 4.5 * inch])
            t_data.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(t_data)
            elements.append(Spacer(1, 10))

        # Trends & Anomalies
        if trend_data:
            elements.append(Paragraph("4. Time-Series Trend Analysis", h2_style))
            p_trend = (
                f"Pollutant: <b>{trend_data.get('pollutant')}</b> | Direction: <b>{trend_data.get('trend_direction')}</b> | "
                f"Rate of Change: {trend_data.get('change_percentage')}%\n"
                f"{trend_data.get('coverage_note', '')}"
            )
            elements.append(Paragraph(p_trend, body_style))
            elements.append(Spacer(1, 8))

        if anomaly_data:
            elements.append(Paragraph("5. Anomaly Detection Summary", h2_style))
            a_info = (
                f"Examined {anomaly_data.get('total_records_examined')} records using {anomaly_data.get('method')} method. "
                f"Identified <b>{anomaly_data.get('anomaly_count')}</b> anomalous event(s) "
                f"({anomaly_data.get('anomaly_percentage')}% of dataset). "
                f"Acceptable range: [{anomaly_data.get('lower_bound')}, {anomaly_data.get('upper_bound')}]."
            )
            elements.append(Paragraph(a_info, body_style))
            elements.append(Spacer(1, 8))

        # Limitations & Disclaimer
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9ca3af"), spaceBefore=6, spaceAfter=8))
        elements.append(Paragraph("Regulatory Notice & Limitations", h2_style))
        disclaimer_text = (
            "This report is generated autonomously by the GreenAir AI Agent for analytical, educational, and decision-support purposes. "
            "Model classifications reflect patterns learned by a supervised machine-learning model from training data and do not substitute "
            "for official regulatory Air Quality Index (AQI) determinations published by government environmental authorities. "
            "Statistical anomalies indicate mathematical outliers in sample distributions and should not be interpreted as confirmed sensor failures "
            "or emergency incidents without ground-truth physical verification. This document does not provide personalized medical diagnoses."
        )
        elements.append(Paragraph(disclaimer_text, disclaimer_style))

        doc.build(elements)

        file_size = os.path.getsize(file_path)

        return {
            "report_id": report_id,
            "filename": filename,
            "stored_path": str(file_path),
            "file_type": "pdf",
            "size_bytes": file_size,
            "title": title,
            "download_url": f"/api/reports/{report_id}/download",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_findings": findings,
        }

    @classmethod
    def generate_csv_report(
        cls,
        title: str,
        data_rows: List[Dict[str, Any]],
        summary_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a structured CSV export report."""
        report_id = str(uuid.uuid4())
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"GreenAir_Data_{safe_title}_{timestamp_str}_{report_id[:8]}.csv"
        file_path = settings.REPORTS_DIR / filename

        df = pd.DataFrame(data_rows)
        df.to_csv(file_path, index=False)
        file_size = os.path.getsize(file_path)

        findings = [f"Exported {len(df)} rows with {len(df.columns)} columns to CSV."]
        if summary_metrics:
            for k, v in summary_metrics.items():
                findings.append(f"{k}: {v}")

        return {
            "report_id": report_id,
            "filename": filename,
            "stored_path": str(file_path),
            "file_type": "csv",
            "size_bytes": file_size,
            "title": title,
            "download_url": f"/api/reports/{report_id}/download",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_findings": findings,
        }

report_service = ReportService()
