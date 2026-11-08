
"""Read-only, multi-viewport website capture for OmniSight-AI."""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import logging
import os
import socket
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from playwright.sync_api import (
    Error as PlaywrightError,
    sync_playwright,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

VIEWPORTS = {
    "mobile_small": {"width": 320, "height": 720},
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 900},
}

LOGGER = logging.getLogger("omnisight.website_capture")


@dataclass(frozen=True, slots=True)
class CaptureConfig:
    url: str
    output_dir: Path
    timeout_ms: int = 30_000

    def __post_init__(self) -> None:
        validate_public_url(self.url)

        if self.timeout_ms <= 0:
            raise ValueError("Timeout must be greater than zero.")


def validate_public_url(url: str) -> None:
    """Reject unsafe destinations, with an opt-in local demo exception."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A website URL is required.")

    parsed = urlparse(url.strip())

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid website URL.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid URL port.") from exc

    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid URL port.")

    hostname = parsed.hostname.lower().rstrip(".")

    # Explicitly allow only the dedicated local demo server.
    local_demo_enabled = os.getenv("OMNISIGHT_ALLOW_LOCAL_TEST_URL") == "1"

    if (
        local_demo_enabled
        and parsed.scheme == "http"
        and hostname == "127.0.0.1"
        and port == 5174
    ):
        return

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost destinations are not allowed.")

    if hostname == "metadata.google.internal":
        raise ValueError("Cloud metadata destinations are not allowed.")

    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(
                    hostname,
                    port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except socket.gaierror as exc:
            raise ValueError("Unable to resolve website hostname.") from exc

    if not addresses:
        raise ValueError("Website hostname has no valid IP address.")

    for address in addresses:
        if not address.is_global:
            raise ValueError(
                "Private, local and reserved network destinations are blocked."
            )

def check_request_destination(route) -> None:
    """Block browser requests to private or reserved destinations."""
    try:
        validate_public_url(route.request.url)
    except (ValueError, OSError):
        LOGGER.warning("Blocked unsafe browser request: %s", route.request.url)
        route.abort()
    else:
        route.continue_()


def capture_website(config: CaptureConfig) -> dict:
    """Capture website HTML and screenshots at four viewport sizes."""
    run_id = uuid4().hex
    run_dir = config.output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    captures = {}
    browser_errors = []

    LOGGER.info("Starting website inspection: %s", config.url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            for name, viewport in VIEWPORTS.items():
                context = browser.new_context(
                    viewport=viewport,
                    device_scale_factor=1,
                )

                page = context.new_page()
                page.set_default_navigation_timeout(config.timeout_ms)

                page.on(
                    "pageerror",
                    lambda error: browser_errors.append(str(error)),
                )

                page.route("**/*", check_request_destination)

                try:
                    response = page.goto(
                        config.url,
                        wait_until="domcontentloaded",
                        timeout=config.timeout_ms,
                    )

                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=5_000,
                        )
                    except PlaywrightError:
                        LOGGER.debug("Network idle timeout: %s", name)

                    if name == "mobile":
                        html_path = run_dir / "website.html"
                        html_path.write_text(
                            page.content(),
                            encoding="utf-8",
                        )

                    screenshot_path = run_dir / f"{name}.png"

                    page.screenshot(
                        path=str(screenshot_path),
                        full_page=True,
                        animations="disabled",
                        timeout=config.timeout_ms,
                    )

                    dimensions = page.evaluate("""() => ({
                        viewport_width: document.documentElement.clientWidth,
                        document_width: document.documentElement.scrollWidth,
                        viewport_height: document.documentElement.clientHeight,
                        document_height: document.documentElement.scrollHeight
                    })""")

                    captures[name] = {
                        "dimensions": viewport,
                        "screenshot": str(screenshot_path.resolve()),
                        "http_status": response.status if response else None,
                        "title": page.title(),
                        "final_url": page.url,
                        "horizontal_overflow": (
                            dimensions["document_width"]
                            > dimensions["viewport_width"]
                        ),
                        "page_dimensions": dimensions,
                    }

                except PlaywrightError as exc:
                    raise RuntimeError(
                        f"Capture failed at {name}: {exc}"
                    ) from exc

                finally:
                    context.close()

        finally:
            browser.close()

    report = {
        "run_id": run_id,
        "url": config.url,
        "final_url": captures["mobile"]["final_url"],
        "title": captures["mobile"]["title"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "capture_status": "completed",
        "html_path": str((run_dir / "website.html").resolve()),
        "viewports": captures,
        "browser_errors": browser_errors,
    }

    report_path = run_dir / "capture_report.json"
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    LOGGER.info("Website capture completed: %s", run_dir)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture a website for OmniSight-AI."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=30_000)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    try:
        config = CaptureConfig(
            url=args.url,
            output_dir=ARTIFACTS_DIR / "website_runs",
            timeout_ms=args.timeout,
        )

        result = capture_website(config)
        print(json.dumps(result, indent=2))

    except (ValueError, OSError, RuntimeError) as exc:
        LOGGER.error("Website capture failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
