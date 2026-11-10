
import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from browser_agent.website_capture import (
    CaptureConfig,
    capture_website,
)
from github_integration.verification import (
    validate_browser_report as validate_report,
)
from repair_engine.browser_verifier import verify_website
from repair_engine.recommend import create_recommendation_report
from vision_engine.inspect_ui import inspect_html


ROOT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
REPORT_PATH = ARTIFACTS_DIR / "browser_verification_report.json"

WEBSITE_RUNS_DIR = ARTIFACTS_DIR / "website_runs"

STAGES = [
    ("Checkout capture", "browser_agent.checkout"),
    ("UI inspection", "vision_engine.inspect_ui"),
    ("Repair recommendations", "repair_engine.recommend"),
    ("Self-healing verification", "repair_engine.self_heal"),
    ("React browser verification", "repair_engine.browser_verifier"),
]


def run_stage(name: str, module: str) -> None:
    print(f"\n{'=' * 12} {name} {'=' * 12}", flush=True)

    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}."
        )

    print(f"{name}: completed", flush=True)


def validate_browser_report() -> str:
    """Validate and return the current local checkout run ID."""
    report = validate_report(REPORT_PATH)
    run_id = report["run_id"]

    print(
        f"Browser verification report validated. Run ID: {run_id}",
        flush=True,
    )
    return run_id


def run_local_pipeline() -> int:
    """Run the existing local checkout and self-healing workflow."""
    latest_run_id = None

    for name, module in STAGES:
        run_stage(name, module)

        if module == "repair_engine.browser_verifier":
            latest_run_id = validate_browser_report()

    if latest_run_id is None:
        raise RuntimeError("Browser verification did not run.")

    print("\nLocal checkout pipeline completed successfully.")
    return 0


def run_website_pipeline(url: str, output_dir: Path) -> dict:
    """Inspect an external website without modifying its source."""
    print("\nStarting read-only website inspection.")
    print(f"Website: {url}")

    # Stage 1: Capture the website.
    print("\n========== Website capture ==========")

    capture_report = capture_website(
        CaptureConfig(
            url=url,
            output_dir=output_dir,
        )
    )

    run_id = capture_report["run_id"]
    run_dir = Path(capture_report["html_path"]).parent

    print(f"Capture completed. Run ID: {run_id}")

    # Stage 2: Inspect HTML and screenshot.
    print("\n========== UI inspection ==========")

    inspection_path = run_dir / "ui_inspection_report.json"

    inspection_report = inspect_html(
        html_path=Path(capture_report["html_path"]),
        screenshot_path=run_dir / "mobile.png",
        report_path=inspection_path,
        website_mode=True,
    )

    print(
        f"Inspection completed. "
        f"Defects: {inspection_report['defects_found']}"
    )

    # Stage 3: Generate repair recommendations.
    print("\n========== Repair recommendations ==========")

    recommendation_path = run_dir / "repair_recommendations.json"

    recommendation_report = create_recommendation_report(
        inspection_path,
        recommendation_path,
    )

    print(
        "Recommendations generated: "
        f"{recommendation_report['recommendations_count']}"
    )

    # Stage 4: Verify the website at four viewports.
    print("\n========== Browser verification ==========")

    verification_report = verify_website(
        url=url,
        output_dir=run_dir,
        run_id=run_id,
        inspection_path=inspection_path,
    )

    print(
        "Browser verification: "
        f"{verification_report['overall_status']}"
    )

    result = {
        "run_id": run_id,
        "url": url,
        "pipeline_status": (
            "completed"
            if verification_report["overall_status"] == "passed"
            else "verification_failed"
        ),
        "capture": capture_report,
        "inspection": inspection_report,
        "recommendations": recommendation_report,
        "verification": verification_report,
        "report_directory": str(run_dir.resolve()),
    }

    summary_path = run_dir / "pipeline_report.json"
    summary_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("\n========== Pipeline summary ==========")
    print(f"Run ID: {run_id}")
    print(f"Status: {result['pipeline_status']}")
    print(f"Reports: {run_dir.resolve()}")
    print(f"Summary: {summary_path.resolve()}")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OmniSight-AI website QA pipeline."
    )

    parser.add_argument(
        "--url",
        help="External website URL for read-only inspection.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WEBSITE_RUNS_DIR,
        help="Directory for external website inspection runs.",
    )

    args = parser.parse_args(argv)

    try:
        if args.url:
            result = run_website_pipeline(
                url=args.url,
                output_dir=args.output_dir,
            )

            return (
                0
                if result["pipeline_status"] == "completed"
                else 1
            )

        return run_local_pipeline()

    except Exception as error:
        print(
            f"\nPipeline stopped: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
