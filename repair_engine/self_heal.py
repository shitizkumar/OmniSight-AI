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
    """Apply CSS to a local browser DOM and capture a screenshot."""
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
        type(width) is not int or type(height) is not int
        or width <= 0 or height <= 0
    ):
        raise ValueError("Viewport dimensions must be positive integers.")

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    html = html_path.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport=viewport)
            page.set_content(html, wait_until="domcontentloaded")
            page.add_style_tag(content=css_patch)

            dimensions = page.evaluate("""() => ({
                viewport_width: document.documentElement.clientWidth,
                document_width: document.documentElement.scrollWidth
            })""")

            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )
        finally:
            browser.close()

    result = {
        "status": "css_applied",
        "application_method": "local_browser_dom",
        "screenshot": str(screenshot_path),
        "css_patch": css_patch,
        "horizontal_overflow": (
            dimensions["document_width"] > dimensions["viewport_width"]
        ),
        "dimensions": dimensions,
        "source_code_modified": False,
    }

    report_path = screenshot_path.with_name("self_heal_report.json")
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
