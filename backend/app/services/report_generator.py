import json
import html
from datetime import datetime
from typing import Dict, Any, List
from jinja2 import Template

HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CodeSentinel AI Analysis Report - {{ project_name }}</title>
  <style>
    :root {
      --bg-main: #0b0f19;
      --bg-card: #151d30;
      --border: #23314d;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent-blue: #3b82f6;
      --critical: #ef4444;
      --high: #f97316;
      --medium: #f59e0b;
      --low: #3b82f6;
      --info: #64748b;
    }
    body {
      background-color: var(--bg-main);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 32px 20px;
    }
    .container {
      max-width: 1000px;
      margin: 0 auto;
    }
    .header {
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
      margin-bottom: 32px;
    }
    .title {
      font-size: 28px;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .badge {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 9999px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; }
    .badge-high { background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid #f97316; }
    .badge-medium { background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid #f59e0b; }
    .badge-low { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid #3b82f6; }
    .badge-info { background: rgba(100, 116, 139, 0.2); color: #cbd5e1; border: 1px solid #64748b; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }
    .card {
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    .card-label {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }
    .card-value {
      font-size: 24px;
      font-weight: 700;
      color: #ffffff;
    }
    .section-title {
      font-size: 20px;
      font-weight: 600;
      margin: 32px 0 16px 0;
      color: #ffffff;
    }
    .finding-card {
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .finding-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 8px;
    }
    .finding-title {
      font-size: 16px;
      font-weight: 600;
      color: #ffffff;
    }
    .finding-loc {
      font-size: 13px;
      color: var(--text-muted);
      font-family: monospace;
      margin-bottom: 12px;
    }
    .finding-text {
      font-size: 14px;
      line-height: 1.6;
      color: #cbd5e1;
      margin-bottom: 12px;
    }
    .code-block {
      background: #060a12;
      border: 1px solid #1a2336;
      border-radius: 6px;
      padding: 12px;
      font-family: Consolas, monospace;
      font-size: 13px;
      color: #38bdf8;
      overflow-x: auto;
      margin-bottom: 12px;
    }
    .remediation-box {
      background: rgba(59, 130, 246, 0.08);
      border-left: 3px solid var(--accent-blue);
      padding: 12px;
      font-size: 13px;
      color: #bfdbfe;
    }
    .footer {
      margin-top: 48px;
      border-top: 1px solid var(--border);
      padding-top: 24px;
      font-size: 13px;
      color: var(--text-muted);
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="title">CodeSentinel AI Quality & Security Report</h1>
      <p style="color: var(--text-muted); margin: 0;">Project: <strong>{{ project_name }}</strong> | Analysis ID: <code>{{ analysis_id }}</code> | Date: {{ generated_at }}</p>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-label">Total Files Analyzed</div>
        <div class="card-value">{{ total_files }}</div>
      </div>
      <div class="card">
        <div class="card-label">Lines of Code</div>
        <div class="card-value">{{ total_lines }}</div>
      </div>
      <div class="card">
        <div class="card-label">Total Findings</div>
        <div class="card-value">{{ total_findings }}</div>
      </div>
      <div class="card">
        <div class="card-label">Critical / High Severity</div>
        <div class="card-value" style="color: #fca5a5;">{{ critical_high_count }}</div>
      </div>
    </div>

    <h2 class="section-title">Analyzers Execution Summary</h2>
    <div class="card" style="margin-bottom: 32px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <thead>
          <tr style="text-align: left; border-bottom: 1px solid var(--border); color: var(--text-muted);">
            <th style="padding: 8px;">Analyzer</th>
            <th style="padding: 8px;">Status</th>
            <th style="padding: 8px;">Duration</th>
            <th style="padding: 8px;">Findings</th>
            <th style="padding: 8px;">Notes</th>
          </tr>
        </thead>
        <tbody>
          {% for r in analyzer_records %}
          <tr style="border-bottom: 1px solid #1c273e;">
            <td style="padding: 8px; font-weight: 600;">{{ r.analyzer_name }}</td>
            <td style="padding: 8px;">
              <span class="badge {% if r.status == 'SUCCESS' %}badge-low{% elif r.status == 'SKIPPED' %}badge-info{% else %}badge-critical{% endif %}">
                {{ r.status }}
              </span>
            </td>
            <td style="padding: 8px;">{{ r.duration_seconds }}s</td>
            <td style="padding: 8px;">{{ r.findings_count }}</td>
            <td style="padding: 8px; color: var(--text-muted);">{{ r.message or r.skip_reason or '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <h2 class="section-title">Detailed Findings ({{ total_findings }})</h2>
    {% if findings %}
      {% for f in findings %}
      <div class="finding-card">
        <div class="finding-header">
          <div>
            <span class="badge badge-{{ f.severity.lower() }}">{{ f.severity }}</span>
            <span class="badge badge-info" style="margin-left: 6px;">{{ f.category }}</span>
            {% if f.is_ai_suggested %}
            <span class="badge" style="background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border: 1px solid #8b5cf6; margin-left: 6px;">
              {% if f.is_demo %}Demo AI{% else %}AI Review{% endif %}
            </span>
            {% endif %}
          </div>
          <span style="font-size: 12px; color: var(--text-muted); font-family: monospace;">{{ f.rule_id }}</span>
        </div>
        <div class="finding-title">{{ f.title }}</div>
        <div class="finding-loc">File: {{ f.file_path }} (Line {{ f.start_line }}{% if f.end_line and f.end_line != f.start_line %}-{{ f.end_line }}{% endif %})</div>
        <div class="finding-text">{{ f.explanation }}</div>
        {% if f.evidence %}
        <div class="code-block">{{ f.evidence }}</div>
        {% endif %}
        {% if f.remediation %}
        <div class="remediation-box">
          <strong>Suggested Remediation:</strong><br>
          {{ f.remediation }}
        </div>
        {% endif %}
      </div>
      {% endfor %}
    {% else %}
      <div class="card" style="text-align: center; color: var(--text-muted); padding: 32px;">
        No code quality, bug risk, or security findings were identified.
      </div>
    {% endif %}

    <div class="footer">
      Generated automatically by CodeSentinel AI Platform. Analysis based on deterministic static rules, cross-file graphs, and optional AI code review.
    </div>
  </div>
</body>
</html>
"""


class ReportGenerator:
    @staticmethod
    def generate_json_report(data: Dict[str, Any]) -> str:
        """Generates clean JSON report."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def generate_markdown_report(data: Dict[str, Any]) -> str:
        """Generates standard GitHub-flavored Markdown report."""
        proj = data.get("project_name", "Unknown Project")
        aid = data.get("analysis_id", "N/A")
        ts = data.get("generated_at", "")
        total_f = data.get("total_findings", 0)
        files = data.get("total_files", 0)
        loc = data.get("total_lines", 0)

        lines = [
            f"# CodeSentinel AI Code Review & Security Report",
            f"",
            f"**Project:** {proj}  ",
            f"**Analysis ID:** `{aid}`  ",
            f"**Generated:** {ts}  ",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"| Metric | Value |",
            f"|---|---|",
            f"| **Files Scanned** | {files} |",
            f"| **Lines of Code** | {loc} |",
            f"| **Total Findings** | {total_f} |",
            f"",
            f"### Findings By Severity",
            f"",
        ]

        sev_counts = data.get("findings_by_severity", {})
        for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]:
            lines.append(f"- **{s}**: {sev_counts.get(s, 0)}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## Analyzers Executed",
            f"",
            f"| Analyzer | Status | Duration | Findings | Notes |",
            f"|---|---|---|---|---|",
        ])

        for r in data.get("analyzer_records", []):
            name = r.get("analyzer_name")
            st = r.get("status")
            dur = f"{r.get('duration_seconds', 0)}s"
            cnt = r.get("findings_count", 0)
            notes = r.get("message") or r.get("skip_reason") or "-"
            lines.append(f"| {name} | {st} | {dur} | {cnt} | {notes} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## Detailed Findings",
            f"",
        ])

        findings = data.get("findings", [])
        if not findings:
            lines.append("No security, quality, or logic flaws detected.")
        else:
            for idx, f in enumerate(findings, start=1):
                title = f.get("title", "")
                sev = f.get("severity", "MEDIUM")
                rule = f.get("rule_id", "")
                fpath = f.get("file_path", "")
                sline = f.get("start_line", 1)
                expl = f.get("explanation", "")
                ev = f.get("evidence", "")
                rem = f.get("remediation", "")
                ai_badge = " *(AI-Suggested)*" if f.get("is_ai_suggested") else ""

                lines.extend([
                    f"### {idx}. [{sev}] {title}{ai_badge}",
                    f"- **Rule ID:** `{rule}`",
                    f"- **Location:** `{fpath}:{sline}`",
                    f"- **Category:** `{f.get('category')}`",
                    f"- **Verification Status:** `{f.get('verification_status')}`",
                    f"",
                    f"**Explanation:**",
                    f"{expl}",
                    f"",
                ])

                if ev:
                    lines.extend([
                        f"**Evidence:**",
                        f"```",
                        f"{ev}",
                        f"```",
                        f"",
                    ])

                if rem:
                    lines.extend([
                        f"**Suggested Remediation:**",
                        f"{rem}",
                        f"",
                    ])

                lines.append("---")

        return "\n".join(lines)

    @classmethod
    def generate_html_report(cls, data: Dict[str, Any]) -> str:
        """Renders standalone self-contained responsive HTML report."""
        # Sanitize data entries to protect against XSS in reports
        safe_data = {
            "project_name": html.escape(str(data.get("project_name", ""))),
            "analysis_id": html.escape(str(data.get("analysis_id", ""))),
            "generated_at": html.escape(str(data.get("generated_at", ""))),
            "total_files": data.get("total_files", 0),
            "total_lines": data.get("total_lines", 0),
            "total_findings": data.get("total_findings", 0),
            "critical_high_count": (
                data.get("findings_by_severity", {}).get("CRITICAL", 0) +
                data.get("findings_by_severity", {}).get("HIGH", 0)
            ),
            "analyzer_records": data.get("analyzer_records", []),
            "findings": []
        }

        for f in data.get("findings", []):
            safe_data["findings"].append({
                "rule_id": html.escape(str(f.get("rule_id", ""))),
                "severity": html.escape(str(f.get("severity", ""))),
                "category": html.escape(str(f.get("category", ""))),
                "title": html.escape(str(f.get("title", ""))),
                "file_path": html.escape(str(f.get("file_path", ""))),
                "start_line": f.get("start_line", 1),
                "end_line": f.get("end_line"),
                "explanation": html.escape(str(f.get("explanation", ""))),
                "evidence": html.escape(str(f.get("evidence", ""))) if f.get("evidence") else None,
                "remediation": html.escape(str(f.get("remediation", ""))) if f.get("remediation") else None,
                "is_ai_suggested": f.get("is_ai_suggested", False),
                "is_demo": f.get("is_demo", False),
            })

        template = Template(HTML_REPORT_TEMPLATE)
        return template.render(**safe_data)
