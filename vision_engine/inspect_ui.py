
"""Website and checkout UI inspection for OmniSight-AI."""

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from vision_engine.vlm_client import analyze_ui


ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"

HTML_PATH = ARTIFACTS_DIR / "checkout.html"
SCREENSHOT_PATH = ARTIFACTS_DIR / "checkout_phone.png"
REPORT_PATH = ARTIFACTS_DIR / "ui_inspection_report.json"

EXPECTED_CONTROLS = {
    "full_name": 'input[name="fullName"], input[name="name"]',
    "email": 'input[type="email"]',
    "submit_button": 'button[type="submit"], button',
}


def inspect_html(
    html_path: Path = HTML_PATH,
    screenshot_path: Path = SCREENSHOT_PATH,
    report_path: Path = REPORT_PATH,
    website_mode: bool = False,
) -> dict:
    """Inspect an HTML snapshot using local checks or a VLM."""
    html_path = Path(html_path)
    screenshot_path = Path(screenshot_path)
    report_path = Path(report_path)

    if not html_path.is_file():
        raise FileNotFoundError(f"HTML snapshot not found: {html_path}")

    provider = os.getenv("VLM_PROVIDER", "openai").strip().lower()

    if provider == "local":
        report = inspect_locally(html_path, website_mode)
    elif provider in {"openai", "xai", "groq"}:
        if not screenshot_path.is_file():
            raise FileNotFoundError(
                f"Screenshot not found: {screenshot_path}"
            )
        report = analyze_ui(screenshot_path, html_path)
    else:
        raise ValueError(
            f"Unsupported VLM_PROVIDER '{provider}'. "
            "Use local, openai, xai, or groq."
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    return report


def inspect_locally(
    html_path: Path = HTML_PATH,
    website_mode: bool = False,
) -> dict:
    """Run local accessibility and responsive-layout checks."""
    html = Path(html_path).read_text(encoding="utf-8")
    defects = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            page = browser.new_page(
                viewport={"width": 320, "height": 720}
            )
            page.set_content(html, wait_until="domcontentloaded")

            if not website_mode:
                for name, selector in EXPECTED_CONTROLS.items():
                    if page.locator(selector).count() == 0:
                        defects.append({
                            "element": name,
                            "issue": "Expected checkout control was not found.",
                            "severity": "high",
                            "evidence": f"No element matched: {selector}",
                            "suggested_fix": "Review the checkout markup.",
                        })

            controls = page.locator("input, select, textarea")

            for index in range(controls.count()):
                control = controls.nth(index)
                input_type = (
                    control.get_attribute("type") or ""
                ).lower()

                if input_type in {"hidden", "submit", "button", "reset"}:
                    continue

                control_id = control.get_attribute("id")
                has_label = (
                    bool(control.get_attribute("aria-label"))
                    or bool(control.get_attribute("aria-labelledby"))
                    or (
                        bool(control_id)
                        and page.locator(
                            f'label[for="{control_id}"]'
                        ).count() > 0
                    )
                    or control.locator(
                        "xpath=ancestor::label"
                    ).count() > 0
                )

                if not has_label:
                    defects.append({
                        "element": (
                            control.get_attribute("name")
                            or f"control_{index}"
                        ),
                        "issue": "Form control may lack an accessible label.",
                        "severity": "medium",
                        "evidence": (
                            f"Control index {index} has no detected label."
                        ),
                        "suggested_fix": (
                            "Add a visible label or accessible name."
                        ),
                    })

            dimensions = page.evaluate("""() => ({
                viewportWidth: document.documentElement.clientWidth,
                documentWidth: document.documentElement.scrollWidth
            })""")

            if dimensions["documentWidth"] > dimensions["viewportWidth"]:
                defects.append({
                    "element": "page_layout",
                    "issue": "Horizontal overflow detected at mobile width.",
                    "severity": "high",
                    "evidence": json.dumps(dimensions),
                    "suggested_fix": (
                        "Review fixed widths and responsive CSS."
                    ),
                })

        finally:
            browser.close()

    severity_summary = {
        severity: sum(
            defect["severity"] == severity for defect in defects
        )
        for severity in ("critical", "high", "medium", "low")
    }

    return {
        "inspection_status": "completed",
        "inspection_method": "local_html_checks",
        "ai_vision_used": False,
        "defects_found": len(defects),
        "severity_summary": severity_summary,
        "defects": defects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect website UI for OmniSight-AI."
    )
    parser.add_argument("--html", type=Path, default=HTML_PATH)
    parser.add_argument("--screenshot", type=Path, default=SCREENSHOT_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument(
        "--website-mode",
        action="store_true",
        help="Use generic website checks instead of checkout checks.",
    )

    args = parser.parse_args()

    result = inspect_html(
        html_path=args.html,
        screenshot_path=args.screenshot,
        report_path=args.output,
        website_mode=args.website_mode,
    )

    print(json.dumps(result, indent=2))
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
