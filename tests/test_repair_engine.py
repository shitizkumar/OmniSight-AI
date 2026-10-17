import pytest

from repair_engine.recommend import generate_recommendations


def test_no_defects_returns_empty_recommendations():
    report = {"defects": []}

    result = generate_recommendations(report)

    assert result["recommendation_status"] == "completed"
    assert result["recommendations_count"] == 0
    assert result["recommendations"] == []
    assert result["automatic_changes_applied"] is False


def test_mobile_overflow_generates_recommendation():
    report = {
        "defects": [
            {
                "element": "page_layout",
                "issue": "Horizontal overflow detected at mobile width.",
                "severity": "high",
                "evidence": "documentWidth: 400, viewportWidth: 320",
            }
        ]
    }

    result = generate_recommendations(report)

    assert result["recommendations_count"] == 1
    assert "responsive widths" in (
        result["recommendations"][0]["recommended_action"]
    )
    assert result["recommendations"][0]["automatic_changes_applied"] is False


def test_accessibility_issue_generates_recommendation():
    report = {
        "defects": [
            {
                "element": "email",
                "issue": "Form control may lack an accessible label.",
                "severity": "medium",
            }
        ]
    }

    result = generate_recommendations(report)

    assert result["recommendations_count"] == 1
    assert "accessible name" in (
        result["recommendations"][0]["recommended_action"]
    )


def test_invalid_report_is_rejected():
    with pytest.raises(ValueError):
        generate_recommendations({"inspection_status": "completed"})


def test_unknown_issue_uses_fallback():
    report = {
        "defects": [
            {
                "element": "header",
                "issue": "Unexpected UI issue.",
                "suggested_fix": "Review the header layout.",
            }
        ]
    }

    result = generate_recommendations(report)

    assert result["recommendations_count"] == 1
    assert result["recommendations"][0]["recommended_action"] == (
        "Review the header layout."
    )