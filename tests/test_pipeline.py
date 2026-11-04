
import json
import subprocess
import uuid

import pytest

import run_pipeline


EXPECTED_STAGES = [
    "browser_agent.checkout",
    "vision_engine.inspect_ui",
    "repair_engine.recommend",
    "repair_engine.self_heal",
    "repair_engine.browser_verifier",
]


def create_valid_report():
    return {
        "run_id": str(uuid.uuid4()),
        "verification_method": "playwright_browser",
        "overall_status": "passed",
        "viewports": {
            name: {
                "status": "passed",
                "checks": {
                    "http_ok": True,
                    "heading_visible": True,
                    "checkout_form_visible": True,
                    "required_fields_present": True,
                    "submit_button_visible": True,
                    "no_horizontal_overflow": True,
                    "no_browser_errors": True,
                    **(
                        {"checkout_submission": True}
                        if name == "mobile"
                        else {}
                    ),
                },
                "browser_errors": [],
            }
            for name in (
                "mobile_small",
                "mobile",
                "tablet",
                "desktop",
            )
        },
    }


def test_pipeline_runs_stages_in_order(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        run_pipeline,
        "REPORT_PATH",
        tmp_path / "browser_verification_report.json",
    )

    run_pipeline.REPORT_PATH.write_text(
        json.dumps(create_valid_report()),
        encoding="utf-8",
    )

    def fake_run(command, cwd, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)

    result = run_pipeline.main()

    assert result == 0
    assert [call[-1] for call in calls] == EXPECTED_STAGES


def test_pipeline_stops_when_a_stage_fails(monkeypatch, capsys):
    calls = []

    def fake_run(command, cwd, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)

    result = run_pipeline.main()
    output = capsys.readouterr()

    assert result == 1
    assert len(calls) == 1
    assert "Pipeline stopped" in output.err
    assert "Checkout capture failed" in output.err


def test_run_stage_reports_failure(monkeypatch):
    def fake_run(command, cwd, check):
        return subprocess.CompletedProcess(command, 2)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="exit code 2"):
        run_pipeline.run_stage("Test stage", "test.module")


def test_browser_report_rejects_failed_status(monkeypatch, tmp_path):
    report_path = tmp_path / "report.json"
    report = create_valid_report()
    report["overall_status"] = "failed"

    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "REPORT_PATH", report_path)

    with pytest.raises(RuntimeError, match="did not pass"):
        run_pipeline.validate_browser_report()


def test_browser_report_rejects_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_pipeline,
        "REPORT_PATH",
        tmp_path / "missing.json",
    )

    with pytest.raises(RuntimeError, match="missing"):
        run_pipeline.validate_browser_report()


def test_browser_report_rejects_invalid_json(monkeypatch, tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text("{invalid json", encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "REPORT_PATH", report_path)

    with pytest.raises(RuntimeError, match="invalid"):
        run_pipeline.validate_browser_report()


def test_browser_report_rejects_failed_viewport(monkeypatch, tmp_path):
    report_path = tmp_path / "report.json"
    report = create_valid_report()
    report["viewports"]["tablet"]["status"] = "failed"

    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "REPORT_PATH", report_path)

    with pytest.raises(RuntimeError, match="tablet"):
        run_pipeline.validate_browser_report()


def test_browser_report_rejects_invalid_run_id(monkeypatch, tmp_path):
    report_path = tmp_path / "report.json"
    report = create_valid_report()
    report["run_id"] = "invalid-id"

    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(run_pipeline, "REPORT_PATH", report_path)

    with pytest.raises(RuntimeError, match="invalid run ID"):
        run_pipeline.validate_browser_report()
