
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



def inspect_html() -> dict:
    if not HTML_PATH.exists():
        raise FileNotFoundError(
            f"HTML snapshot not found: {HTML_PATH}. "
            "Run python -m browser_agent.checkout first."
        )

    provider = os.getenv("VLM_PROVIDER", "openai").strip().lower()

    if provider == "local":
        report = inspect_locally()
    elif provider in {"openai", "xai"}:
        report = analyze_ui(SCREENSHOT_PATH, HTML_PATH)
    else:
        raise ValueError(
            f"Unsupported VLM_PROVIDER '{provider}'. "
            "Use local, openai, or xai."
        )

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return report

def inspect_locally() -> dict:
    html = HTML_PATH.read_text(encoding="utf-8")
    defects = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 720})

        try:
            page.set_content(html, wait_until="domcontentloaded")

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
                input_type = (control.get_attribute("type") or "").lower()

                if input_type in {"hidden", "submit", "button", "reset"}:
                    continue

                control_id = control.get_attribute("id")
                has_label = (
                    bool(control.get_attribute("aria-label"))
                    or bool(control.get_attribute("aria-labelledby"))
                    or (
                        bool(control_id)
                        and page.locator(f'label[for="{control_id}"]').count() > 0
                    )
                    or control.locator("xpath=ancestor::label").count() > 0
                )

                if not has_label:
                    defects.append({
                        "element": control.get_attribute("name") or f"control_{index}",
                        "issue": "Form control may lack an accessible label.",
                        "severity": "medium",
                        "evidence": f"Control index {index} has no detected label.",
                        "suggested_fix": "Add a visible label or accessible name.",
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
                    "suggested_fix": "Review fixed widths and responsive CSS.",
                })
        finally:
            browser.close()

    return {
        "inspection_status": "completed",
        "inspection_method": "local_html_checks",
        "ai_vision_used": False,
        "defects_found": len(defects),
        "defects": defects,
    }


if __name__ == "__main__":
    print(json.dumps(inspect_html(), indent=2))
    print(f"\nReport saved to: {REPORT_PATH}")
