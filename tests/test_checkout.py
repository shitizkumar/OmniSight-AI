
from browser_agent.checkout import build_responsive_report


def test_report_passes_when_all_viewports_are_clear():
    results = [
        {"viewport": "mobile", "horizontal_overflow": False},
        {"viewport": "desktop", "horizontal_overflow": False},
    ]

    report = build_responsive_report(results)

    assert report["status"] == "passed"
    assert report["viewports_tested"] == 2
    assert report["defects_found"] == 0


def test_report_fails_when_overflow_is_detected():
    results = [
        {"viewport": "mobile", "horizontal_overflow": True},
        {"viewport": "desktop", "horizontal_overflow": False},
    ]

    report = build_responsive_report(results)

    assert report["status"] == "failed"
    assert report["viewports_tested"] == 2
    assert report["defects_found"] == 1

