
import subprocess
import sys
from pathlib import Path

from github_integration.verification import (
    validate_browser_report as validate_report,
)

ROOT_DIR = Path(__file__).resolve().parent
REPORT_PATH = ROOT_DIR / "artifacts" / "browser_verification_report.json"

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
    """Validate and return the current browser verification run ID."""
    report = validate_report(REPORT_PATH)
    run_id = report["run_id"]

    print(
        f"Browser verification report validated. Run ID: {run_id}",
        flush=True,
    )
    return run_id


def main() -> int:
    try:
        latest_run_id = None

        for name, module in STAGES:
            run_stage(name, module)

            if module == "repair_engine.browser_verifier":
                latest_run_id = validate_browser_report()

        if latest_run_id is None:
            raise RuntimeError("Browser verification did not run.")

    except RuntimeError as error:
        print(f"\nPipeline stopped: {error}", file=sys.stderr)
        return 1

    print("\nPipeline completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
