
from fastapi.testclient import TestClient

from backend.webhook import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_failed_build_requires_inspection():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-001",
            "project": "OmniSight-AI",
            "build_status": "failed",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.json()["inspection_required"] is True


def test_successful_build_does_not_require_inspection():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-002",
            "project": "OmniSight-AI",
            "build_status": "success",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.json()["inspection_required"] is False


def test_invalid_build_status_is_rejected():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-003",
            "project": "OmniSight-AI",
            "build_status": "unknown",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 422
def test_url_repair_requires_qa_approval(tmp_path, monkeypatch):
    from backend import webhook

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    run_id = "2a22444ad7294a3394e4e91028720e2"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    response = client.post(
        "/api/qa/repair",
        json={
            "run_id": run_id,
            "css_patch": "body { overflow-x: hidden; }",
        },
    )

    assert response.status_code == 403


def test_url_repair_rejects_missing_overflow_defect(tmp_path, monkeypatch):
    import json
    from backend import webhook

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    run_id = "2a22444ad7294a3394e4e91028720e2"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    reports = {
        "qa_decision.json": {
            "run_id": run_id,
            "decision": "approved",
        },
        "capture_report.json": {
            "run_id": run_id,
        },
        "ui_inspection_report.json": {
            "run_id": run_id,
            "defects": [],
        },
    }

    for filename, data in reports.items():
        (run_dir / filename).write_text(json.dumps(data), encoding="utf-8")

    (run_dir / "website.html").write_text(
        "<html><body>Test page</body></html>",
        encoding="utf-8",
    )

    response = client.post(
        "/api/qa/repair",
        json={
            "run_id": run_id,
            "css_patch": "body { overflow-x: hidden; }",
        },
    )

    assert response.status_code == 409