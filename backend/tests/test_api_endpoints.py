import io
import zipfile
import pytest
from app.models.entities import Project, AnalysisJob, Finding


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_create_and_list_projects(client):
    res = client.post("/api/v1/projects", json={"name": "test-project", "description": "desc"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "test-project"
    assert "id" in data

    list_res = client.get("/api/v1/projects")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_create_analysis_with_source_file(client):
    file_content = b"def insecure():\n    eval('1+1')\n"
    files = {"files": ("main.py", file_content, "text/plain")}
    data = {"project_name": "api-test-project", "options": "{}"}

    res = client.post("/api/v1/analyses", data=data, files=files)
    assert res.status_code == 202
    resp_data = res.json()
    assert "analysis_id" in resp_data

    # Check progress
    aid = resp_data["analysis_id"]
    prog_res = client.get(f"/api/v1/analyses/{aid}/progress")
    assert prog_res.status_code == 200
    assert "progress_percent" in prog_res.json()


def test_finding_verification_status_update(client, db):
    # Setup test finding in DB
    p = Project(name="proj-finding-test")
    db.add(p)
    db.commit()

    job = AnalysisJob(project_id=p.id, status="COMPLETED")
    db.add(job)
    db.commit()

    f = Finding(
        analysis_id=job.id,
        rule_id="TEST-001",
        source_analyzer="python_ast",
        file_path="main.py",
        start_line=10,
        severity="HIGH",
        confidence="HIGH",
        category="SECURITY",
        title="Test Flaw",
        explanation="Testing update",
        is_ai_suggested=False,
        is_demo=False,
        verification_status="UNREVIEWED"
    )
    db.add(f)
    db.commit()

    # Update status to CONFIRMED
    res = client.patch(
        f"/api/v1/findings/{f.id}/status",
        json={"status": "CONFIRMED", "notes": "Audited by security team"}
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "CONFIRMED"

    # Verify audit history
    history = res.json().get("status_history", [])
    assert len(history) == 1
    assert history[0]["old_status"] == "UNREVIEWED"
    assert history[0]["new_status"] == "CONFIRMED"


def test_report_exports(client, db):
    p = Project(name="proj-report-test")
    db.add(p)
    db.commit()

    job = AnalysisJob(project_id=p.id, status="COMPLETED", total_files=1, total_lines=50)
    db.add(job)
    db.commit()

    # JSON export
    res_json = client.get(f"/api/v1/analyses/{job.id}/report?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]

    # HTML export
    res_html = client.get(f"/api/v1/analyses/{job.id}/report?format=html")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "CodeSentinel AI" in res_html.text

    # Markdown export
    res_md = client.get(f"/api/v1/analyses/{job.id}/report?format=markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# CodeSentinel AI" in res_md.text


def test_dashboard_metrics(client):
    res = client.get("/api/v1/stats/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "total_projects" in data
    assert "total_analyses" in data
    assert "findings_by_severity" in data
