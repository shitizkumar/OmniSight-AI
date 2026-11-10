
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
        },
    )

    assert response.status_code == 409

def test_github_pull_request_requires_qa_approval(tmp_path, monkeypatch):
    from backend import webhook

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    run_id = "2a22444ad7294a3394e4e91028720e2"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    response = client.post(
        "/api/qa/github/pull-request",
        json={
            "run_id": run_id,
            "commit_message": "Fix responsive checkout layout",
            "pr_title": "Fix responsive checkout layout",
            "pr_body": "Verified responsive CSS repair.",
        },
    )

    assert response.status_code == 403

def test_github_pull_request_requires_browser_report(tmp_path, monkeypatch):
    import json
    from backend import webhook

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    run_id = "2a22444ad7294a3394e4e91028720e2"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    (run_dir / "qa_decision.json").write_text(
        json.dumps({"run_id": run_id, "decision": "approved"}),
        encoding="utf-8",
    )

    response = client.post(
        "/api/qa/github/pull-request",
        json={
            "run_id": run_id,
            "commit_message": "Fix responsive checkout layout",
            "pr_title": "Fix responsive checkout layout",
            "pr_body": "Verified responsive CSS repair.",
        },
    )

    assert response.status_code == 404


def test_github_pull_request_uses_approved_run_report_and_fixed_file(
    tmp_path, monkeypatch
):
    import json
    from backend import webhook

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    run_id = "2a22444ad7294a3394e4e91028720e2"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    report_path = run_dir / "browser_verification_report.json"

    (run_dir / "qa_decision.json").write_text(
        json.dumps({"run_id": run_id, "decision": "approved"}),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps({"run_id": run_id}),
        encoding="utf-8",
    )

    captured = {}

    def fake_create_pull_request(**kwargs):
        captured.update(kwargs)
        return "https://github.com/shitizkumar/OmniSight-AI/pull/999"

    monkeypatch.setattr(
        webhook,
        "create_pull_request",
        fake_create_pull_request,
    )

    response = client.post(
        "/api/qa/github/pull-request",
        json={
            "run_id": run_id,
            "commit_message": "Fix responsive checkout layout",
            "pr_title": "Fix responsive checkout layout",
            "pr_body": "Verified responsive CSS repair.",
        },
    )

    assert response.status_code == 200
    assert response.json()["pull_request_url"].endswith("/pull/999")
    assert captured["file_path"] == "mock-store/src/App.css"
    assert captured["expected_run_id"] == run_id
    assert captured["report_path"] == report_path

def test_approved_url_repair_completes_browser_preview(tmp_path, monkeypatch):
    import json

    import backend.webhook as webhook

    run_id = "a1b2c3d4e5f6478899aabbccddeeff00"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    monkeypatch.setattr(webhook, "WEBSITE_RUNS_DIR", tmp_path)

    reports = {
        "qa_decision.json": {
            "run_id": run_id,
            "decision": "approved",
        },
        "capture_report.json": {
            "run_id": run_id,
        },
        "ui_inspection_report.json": {
            "defects": [
                {
                    "issue": "Horizontal overflow detected",
                    "severity": "high",
                    "element": ".page",
                }
            ]
        },
    }

    for filename, data in reports.items():
        (run_dir / filename).write_text(
            json.dumps(data),
            encoding="utf-8",
        )

    html = """<!doctype html>
    <html>
    <head>
        <style>
            .page { width: 900px; height: 100px; }
        </style>
    </head>
    <body>
        <div class="page">Test content</div>
    </body>
    </html>
    """

    html_path = run_dir / "website.html"
    html_path.write_text(html, encoding="utf-8")

    monkeypatch.setattr(
        webhook,
        "generate_css_patch",
        lambda **kwargs: {
            "css_patch": ".page { width: 100% !important; box-sizing: border-box; }",
            "explanation": "Make the page container responsive.",
            "provider": "test",
            "model": "test-model",
        },
    )

    response = client.post(
        "/api/qa/repair",
        json={
            "run_id": run_id,
            "viewport_width": 320,
            "viewport_height": 720,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["ai_repair"]["provider"] == "test"
    assert data["verification_status"] == "repair_verified"
    assert data["before"]["horizontal_overflow"] is True
    assert data["after"]["horizontal_overflow"] is False
    assert data["source_code_modified"] is False
    assert data["external_website_modified"] is False
    assert html_path.read_text(encoding="utf-8") == html
