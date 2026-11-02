"""Real-browser verification for the OmniSight React application."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "mock-store"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
REPORT_PATH = ARTIFACTS_DIR / "browser_verification_report.json"

VIEWPORTS = {
    "mobile_small": {"width": 320, "height": 720},
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 900},
}


def wait_for_server(url: str, process: subprocess.Popen) -> None:
    """Wait until the Vite development server responds."""
    for _ in range(40):
        if process.poll() is not None:
            raise RuntimeError("Vite server stopped unexpectedly.")

        try:
            with urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.5)

    raise TimeoutError("Vite server did not start within 20 seconds.")


def verify_checkout() -> dict:
    """Verify the real React application across multiple viewports."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    url = "http://127.0.0.1:4173"
    command = "npm.cmd run dev -- --host 127.0.0.1 --port 4173 --strictPort"
    server = subprocess.Popen(
    command,
    cwd=APP_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    shell=True,
)

    report = {
        "verification_method": "playwright_browser",
        "url": url,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "viewports": {},
        "overall_status": "failed",
    }

    try:
        wait_for_server(url, server)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            try:
                for name, viewport in VIEWPORTS.items():
                    page = browser.new_page(viewport=viewport)
                    errors = []

                    page.on("pageerror", lambda error: errors.append(str(error)))

                    response = page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=30_000,
                    )

                    page.locator("h1").wait_for()

                    page_checks = {
                        "http_ok": bool(response and response.status == 200),
                        "heading_visible": page.get_by_role(
                            "heading",
                            name="Everyday Backpack",
                        ).is_visible(),
                        "checkout_form_visible": page.locator(
                            "form.checkout-form"
                        ).is_visible(),
                        "required_fields_present": all(
                            page.locator(selector).count() == 1
                            for selector in (
                                "#name",
                                "#email",
                                "#address",
                                "#city",
                                "#postalCode",
                            )
                        ),
                        "submit_button_visible": page.locator(
                            "button[type='submit']"
                        ).is_visible(),
                    }

                    dimensions = page.evaluate(
                        """() => ({
                            viewport_width: document.documentElement.clientWidth,
                            page_width: document.documentElement.scrollWidth
                        })"""
                    )

                    page_checks["no_horizontal_overflow"] = (
                        dimensions["page_width"]
                        <= dimensions["viewport_width"]
                    )

                    if name == "mobile":
                        page.locator("#name").fill("OmniSight Test")
                        page.locator("#email").fill("test@example.com")
                        page.locator("#address").fill("Test Street")
                        page.locator("#city").fill("Delhi")
                        page.locator("#postalCode").fill("110001")
                        page.locator("button[type='submit']").click()

                        page_checks["checkout_submission"] = (
                            page.get_by_role("status").is_visible()
                        )

                    screenshot_path = (
                        ARTIFACTS_DIR / f"browser_{name}.png"
                    )

                    page.screenshot(
                        path=str(screenshot_path),
                        full_page=True,
                    )

                    page_checks["no_browser_errors"] = not errors

                    passed = all(page_checks.values())

                    report["viewports"][name] = {
                        "dimensions": viewport,
                        "checks": page_checks,
                        "browser_errors": errors,
                        "screenshot": str(screenshot_path),
                        "status": "passed" if passed else "failed",
                    }

                    page.close()

            finally:
                browser.close()

        report["overall_status"] = (
            "passed"
            if all(
                result["status"] == "passed"
                for result in report["viewports"].values()
            )
            else "failed"
        )

    except Exception as error:
        report["error"] = str(error)

    finally:
        server.terminate()

        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()

        REPORT_PATH.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8",
        )

    return report


if __name__ == "__main__":
    result = verify_checkout()
    print(json.dumps(result, indent=4))

    if result["overall_status"] != "passed":
        raise SystemExit(1)