
"""Generate UI repair recommendations for OmniSight-AI."""

import argparse
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"

REPORT_PATH = ARTIFACTS_DIR / "ui_inspection_report.json"
OUTPUT_PATH = ARTIFACTS_DIR / "repair_recommendations.json"


def generate_recommendations(report: dict) -> dict:
    if not isinstance(report, dict) or not isinstance(
        report.get("defects"), list
    ):
        raise ValueError("Report must contain a defects list.")

    recommendations = []

    for defect in report["defects"]:
        if not isinstance(defect, dict):
            raise ValueError("Each defect must be a JSON object.")

        issue = defect.get("issue", "").lower()

        if "overflow" in issue:
            action = (
                "Use responsive widths and remove fixed-width constraints."
            )
        elif "label" in issue or "accessible" in issue:
            action = "Add a visible label or accessible name."
        else:
            action = defect.get(
                "suggested_fix", "Review the affected UI element."
            )

        recommendations.append({
            "element": defect.get("element", "unknown"),
            "issue": defect.get("issue", "Unspecified UI issue."),
            "severity": defect.get("severity", "medium"),
            "recommended_action": action,
            "automatic_changes_applied": False,
        })

    return {
        "recommendation_status": "completed",
        "source_report": "ui_inspection_report.json",
        "automatic_changes_applied": False,
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
    }


def create_recommendation_report(
    report_path: Path,
    output_path: Path,
) -> dict:
    """Read an inspection report and save its recommendations."""
    report_path = Path(report_path)
    output_path = Path(output_path)

    if not report_path.is_file():
        raise FileNotFoundError(
            f"Inspection report not found: {report_path}"
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = generate_recommendations(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate UI repair recommendations."
    )
    parser.add_argument("--input", type=Path, default=REPORT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    result = create_recommendation_report(
        args.input,
        args.output,
    )

    print(json.dumps(result, indent=2))
    print(f"\nRecommendations saved to: {args.output}")


if __name__ == "__main__":
    main()
