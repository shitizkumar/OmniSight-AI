
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "artifacts"

CHECKOUT_URL = "http://localhost:5173"

VIEWPORTS = {
    "mobile": {"width": 320, "height": 720},
    "phone": {"width": 390, "height": 844},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 900},
}


def automate_checkout() -> list[Path]:
    """Complete a demo checkout and capture responsive screenshots."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = []

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
            page.get_by_label("Street address").fill("123 Test Street")
            page.get_by_label("City").fill("Dehradun")
            page.get_by_label("PIN code").fill("248001")
            page.get_by_label("Quantity").select_option("2")

            page.get_by_role(
                "button",
                name="Place demo order",
            ).click()

            page.get_by_role("status").get_by_text(
                "Demo order submitted successfully",
            ).wait_for()

            # Save the rendered HTML for Day 6 vision inspection.
            html_path = OUTPUT_DIR / "checkout.html"
            html_path.write_text(
                page.content(),
                encoding="utf-8",
            )
            print(f"HTML snapshot: {html_path}")

            # Capture and validate all responsive viewports.
            for name, viewport in VIEWPORTS.items():
                page.set_viewport_size(viewport)

                screenshot_path = OUTPUT_DIR / f"checkout_{name}.png"

                page.screenshot(
                    path=str(screenshot_path),
                    full_page=True,
                    animations="disabled",
                )

                has_horizontal_overflow = page.evaluate(
                    "document.documentElement.scrollWidth > "
                    "document.documentElement.clientWidth"
                )

                if has_horizontal_overflow:
                    raise AssertionError(
                        f"Horizontal overflow detected at {name}: {viewport}"
                    )

                screenshots.append(screenshot_path)

            print("Checkout completed successfully.")
            print("Demo order submitted; no payment was processed.")

            for screenshot in screenshots:
                print(f"Screenshot: {screenshot}")

            return screenshots

        finally:
            browser.close()


if __name__ == "__main__":
    automate_checkout()
