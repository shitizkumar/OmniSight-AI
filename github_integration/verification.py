
import json
import uuid
from pathlib import Path

EXPECTED_VIEWPORTS = {
    "mobile_small",
    "mobile",
    "tablet",
    "desktop",
}

REQUIRED_CHECKS = {
    "http_ok",
    "heading_visible",
    "checkout_form_visible",
    "required_fields_present",
    "submit_button_visible",
    "no_horizontal_overflow",
    "no_browser_errors",
}


def validate_browser_report(
    report_path: Path,
    expected_run_id: str | None = None,
) -> dict:
    """Validate a real Playwright browser verification report."""

    if not report_path.is_file():
        raise RuntimeError("Browser verification report is missing.")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(
            f"Browser verification report is invalid: {error}"
        ) from error

    if not isinstance(report, dict):
        raise RuntimeError("Browser verification report must be a JSON object.")

    run_id = report.get("run_id")

    try:
        uuid.UUID(run_id)
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError("Browser verification report has an invalid run ID.")

    if expected_run_id is not None and run_id != expected_run_id:
        raise RuntimeError("Browser verification report is stale.")

    if report.get("verification_method") != "playwright_browser":
        raise RuntimeError("Report is not from Playwright browser verification.")

    if report.get("overall_status") != "passed":
        raise RuntimeError("Browser verification did not pass.")

    viewports = report.get("viewports")

    if not isinstance(viewports, dict):
        raise RuntimeError("Browser verification has no valid viewport results.")

    if set(viewports) != EXPECTED_VIEWPORTS:
        raise RuntimeError("Browser verification is missing required viewports.")

    for name, result in viewports.items():
        if not isinstance(result, dict):
            raise RuntimeError(f"Invalid result for viewport: {name}")

        if result.get("status") != "passed":
            raise RuntimeError(f"Viewport verification failed: {name}")

        checks = result.get("checks")

        if not isinstance(checks, dict):
            raise RuntimeError(f"Missing checks for viewport: {name}")

        if not REQUIRED_CHECKS.issubset(checks):
            raise RuntimeError(f"Required checks are missing: {name}")

        if not all(value is True for value in checks.values()):
            raise RuntimeError(f"One or more checks failed: {name}")

        if result.get("browser_errors") != []:
            raise RuntimeError(f"Browser errors detected: {name}")

    mobile_checks = viewports["mobile"]["checks"]

    if mobile_checks.get("checkout_submission") is not True:
        raise RuntimeError("Mobile checkout submission was not verified.")

    return report
