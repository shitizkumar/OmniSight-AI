
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "artifacts"
REPORT_PATH = OUTPUT_DIR / "responsive_report.json"

CHECKOUT_URL = "http://localhost:5173"

VIEWPORTS = {
    "mobile": {"width": 320, "height": 720},
    "phone": {"width": 390, "height": 844},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 900},
}


def build_responsive_report(results: list[dict]) -> dict:
    """Summarize responsive viewport checks."""
    defects_found = sum(
        result["horizontal_overflow"] for result in results
    )

    return {
        "status": "failed" if defects_found else "passed",
        "viewports_tested": len(results),
        "defects_found": defects_found,
        "results": results,
    }


def automate_checkout() -> list[Path]:
    """Run demo checkout and report responsive layout results."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = []
    results = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            page = browser.new_page(
                viewport=VIEWPORTS["phone"],
                device_scale_factor=1,
            )
            page.goto(CHECKOUT_URL, wait_until="domcontentloaded")

            page.get_by_label("Full name").fill("Test Customer")
            page.get_by_label("Email address").fill("test@example.com")
            page.get_by_label("Street address").fill("123 TestStreet")
            page.get_by_label("City").fill("Dehradun")
            page.get_by_label("PIN code").fill("248001")
            page.get_by_label("Quantity").select_option("2")
            page.get_by_role("button", name="Place demo order").click()

            page.get_by_role("status").get_by_text(
                "Demo order submitted successfully"
            ).wait_for()

            (OUTPUT_DIR / "checkout.html").write_text(
                page.content(), encoding="utf-8"
            )

            for name, viewport in VIEWPORTS.items():
                page.set_viewport_size(viewport)
                screenshot_path = OUTPUT_DIR / f"checkout_{name}.png"

                page.screenshot(
                    path=str(screenshot_path),
                    full_page=True,
                    animations="disabled",
                )

                dimensions = page.evaluate("""() => ({
                    viewport_width: document.documentElement.clientWidth,
                    document_width: document.documentElement.scrollWidth
                })""")

                results.append({
                    "viewport": name,
                    **viewport,
                    **dimensions,
                    "horizontal_overflow": (
                        dimensions["document_width"]
                        > dimensions["viewport_width"]
                    ),
                    "screenshot": str(
                        screenshot_path.relative_to(PROJECT_ROOT)
                    ),
                })
                screenshots.append(screenshot_path)

            report = build_responsive_report(results)
            REPORT_PATH.write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )

            print(json.dumps(report, indent=2))
            print(f"\nResponsive report saved to: {REPORT_PATH}")

            if report["defects_found"]:
                raise AssertionError(
                    f"Horizontal overflow found in "
                    f"{report['defects_found']} viewport(s)."
                )

            print("Checkout completed successfully.")
            print("Demo order submitted; no payment was processed.")
            return screenshots

        finally:
            browser.close()


if __name__ == "__main__":
    automate_checkout()
