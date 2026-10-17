import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
INPUT_PATH = ARTIFACTS_DIR / "ui_inspection_report.json"
OUTPUT_PATH = ARTIFACTS_DIR / "repair_recommendations.json"

REPAIR_GUIDES = {
    "Horizontal overflow detected at mobile width.": (
        "Review fixed-width elements and use responsive widths, "
        "max-width, and flex-wrap where appropriate."
    ),
    "Form control may lack an accessible label.": (
        "Add an associated visible label or an appropriate "
        "accessible name, then verify it with the inspector."
    ),
    "Expected checkout control was not found.": (
        "Review the checkout markup and confirm the expected "
        "input names, types, and submit button."
    ),
}


def generate_recommendations(report: dict) -> dict:
    if not isinstance(report, dict) or not isinstance(
        report.get("defects"), list
    ):
        raise ValueError("Inspection report must contain a defects list.")

    recommendations = []

    for defect in report["defects"]:
        if not isinstance(defect, dict):
            raise ValueError("Each defect must be a JSON object.")

        issue = defect.get("issue", "Unspecified UI issue.")

        recommendations.append({
            "element": defect.get("element", "unknown"),
            "issue": issue,
            "severity": defect.get("severity", "unknown"),
            "evidence": defect.get("evidence", ""),
            "recommended_action": REPAIR_GUIDES.get(
                issue,
                defect.get(
                    "suggested_fix",
                    "Review the defect manually and verify a safe fix."
                ),
            ),
            "automatic_changes_applied": False,
        })

    return {
        "recommendation_status": "completed",
        "source_report": INPUT_PATH.name,
        "automatic_changes_applied": False,
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Inspection report not found: {INPUT_PATH}"
        )

    try:
        report = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Inspection report contains invalid JSON.") from exc

    result = generate_recommendations(report)
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print(f"\nRecommendations saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()