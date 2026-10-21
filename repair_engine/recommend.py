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


def main() -> None:
    if not REPORT_PATH.exists():
        raise FileNotFoundError(f"Inspection report not found: {REPORT_PATH}")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    result = generate_recommendations(report)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nRecommendations saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()