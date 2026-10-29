
import subprocess

import run_pipeline


def test_pipeline_runs_stages_in_order(monkeypatch):
    calls = []

    def fake_run(command, cwd, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_pipeline.subprocess, "run", fake_run)

    result = run_pipeline.main()

    assert result == 0
    assert [call[-1] for call in calls] == [
        "browser_agent.checkout",
        "vision_engine.inspect_ui",
        "repair_engine.recommend",
        "repair_engine.self_heal",
    ]


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

    try:
        run_pipeline.run_stage("Test stage", "test.module")
    except RuntimeError as exc:
        assert "exit code 2" in str(exc)
    else:
        raise AssertionError("Expected run_stage to raise RuntimeError.")
