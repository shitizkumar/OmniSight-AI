from pathlib import Path
import json

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MAX_CSS_LENGTH = 10_000


def apply_css_patch(
    html_path: Path,
    css_patch: str,
    screenshot_path: Path,
    viewport: dict | None = None,
) -> dict:
    """Apply a CSS patch locally and verify its effect on horizontal overflow."""
    html_path = Path(html_path)
    screenshot_path = Path(screenshot_path)

    if not html_path.is_file():
        raise FileNotFoundError(f"HTML snapshot not found: {html_path}")

    if not isinstance(css_patch, str) or not css_patch.strip():
        raise ValueError("CSS patch must be a non-empty string.")

    if len(css_patch) > MAX_CSS_LENGTH:
        raise ValueError("CSS patch is too long.")

    if "@import" in css_patch.lower() or "javascript:" in css_patch.lower():
        raise ValueError("CSS patch contains a disallowed construct.")

    viewport = viewport or {"width": 320, "height": 720}
    width, height = viewport.get("width"), viewport.get("height")

    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
    ):
        raise ValueError("Viewport dimensions must be positive integers.")

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    html = html_path.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport=viewport)
            page.set_content(html, wait_until="domcontentloaded")

            before_dimensions = page.evaluate("""() => ({
                viewport_width: document.documentElement.clientWidth,
                document_width: document.documentElement.scrollWidth
            })""")
            before_overflow = (
                before_dimensions["document_width"]
                > before_dimensions["viewport_width"]
            )

            page.add_style_tag(content=css_patch)

            after_dimensions = page.evaluate("""() => ({
                viewport_width: document.documentElement.clientWidth,
                document_width: document.documentElement.scrollWidth
            })""")
            after_overflow = (
                after_dimensions["document_width"]
                > after_dimensions["viewport_width"]
            )

            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )
        finally:
            browser.close()

    if before_overflow and not after_overflow:
        verification_status = "repair_verified"
    elif before_overflow and after_overflow:
        verification_status = "repair_failed"
    elif not before_overflow and after_overflow:
        verification_status = "regression_detected"
    else:
        verification_status = "no_repair_needed"

    result = {
        "status": "css_applied",
        "verification_status": verification_status,
        "application_method": "local_browser_dom",
        "screenshot": str(screenshot_path),
        "css_patch": css_patch,
        "before": {
            "horizontal_overflow": before_overflow,
            "dimensions": before_dimensions,
        },
        "after": {
            "horizontal_overflow": after_overflow,
            "dimensions": after_dimensions,
        },
        "horizontal_overflow": after_overflow,
        "source_code_modified": False,
    }

    report_path = screenshot_path.with_name("self_heal_report.json")
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
