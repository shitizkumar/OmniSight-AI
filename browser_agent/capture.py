
"""Reliable browser screenshot capture for OmniSight-AI."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts"

LOGGER = logging.getLogger("omnisight.browser_agent")


@dataclass(frozen=True, slots=True)
class CaptureConfig:
    """Configuration for a single browser capture."""

    url: str = "https://example.com"
    width: int = 390
    height: int = 844
    timeout_ms: int = 30_000
    output_dir: Path = DEFAULT_OUTPUT_DIR
    full_page: bool = False
    headless: bool = True

    def __post_init__(self) -> None:
        parsed_url = urlparse(self.url)

        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("URL must use HTTP or HTTPS.")

        if not parsed_url.hostname:
            raise ValueError("URL must contain a valid hostname.")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Viewport dimensions must be positive.")

        if self.timeout_ms <= 0:
            raise ValueError("Timeout must be greater than zero.")


@dataclass(frozen=True, slots=True)
class CaptureResult:
    """Evidence and metadata returned by a successful capture."""

    url: str
    title: str
    screenshot_path: Path
    viewport: dict[str, int]
    status_code: int | None
    captured_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "url": self.url,
            "title": self.title,
            "screenshot_path": str(self.screenshot_path),
            "viewport": self.viewport,
            "status_code": self.status_code,
            "captured_at": self.captured_at,
        }


def capture_website(config: CaptureConfig) -> CaptureResult:
    """Navigate to a URL and save screenshot evidence.

    Raises:
        OSError: If the output directory or evidence cannot be written.
        PlaywrightError: If browser automation fails.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = config.output_dir / "mobile_screenshot.png"

    LOGGER.info("Starting browser capture for %s", config.url)

    with sync_playwright() as playwright:
        browser = None

        try:
            browser = playwright.chromium.launch(
                headless=config.headless,
            )

            context = browser.new_context(
                viewport={
                    "width": config.width,
                    "height": config.height,
                },
                device_scale_factor=1,
            )

            page = context.new_page()
            page.set_default_navigation_timeout(config.timeout_ms)
            page.set_default_timeout(config.timeout_ms)

            response = page.goto(
                config.url,
                wait_until="domcontentloaded",
                timeout=config.timeout_ms,
            )

            # Network-idle is helpful but not required for every website.
            # Some applications maintain persistent network connections.
            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=min(config.timeout_ms, 5_000),
                )
            except PlaywrightError:
                LOGGER.debug(
                    "Network idle was not reached; capturing current page state."
                )

            page.screenshot(
                path=str(screenshot_path),
                full_page=config.full_page,
                animations="disabled",
                timeout=config.timeout_ms,
            )

            result = CaptureResult(
                url=page.url,
                title=page.title(),
                screenshot_path=screenshot_path.resolve(),
                viewport={
                    "width": config.width,
                    "height": config.height,
                },
                status_code=response.status if response else None,
                captured_at=datetime.now(timezone.utc).isoformat(),
            )

            LOGGER.info(
                "Screenshot saved to %s (HTTP status: %s)",
                result.screenshot_path,
                result.status_code,
            )

            return result

        except (PlaywrightError, OSError):
            LOGGER.exception("Browser capture failed for %s", config.url)
            raise

        finally:
            if browser is not None:
                browser.close()


def main() -> None:
    """Parse command-line options and run a browser capture."""
    parser = argparse.ArgumentParser(
        description="Capture website screenshots for OmniSight-AI."
    )
    parser.add_argument(
        "--url",
        default="https://example.com",
        help="Website URL to capture.",
    )
    parser.add_argument("--width", type=int, default=390)
    parser.add_argument("--height", type=int, default=844)
    parser.add_argument("--timeout", type=int, default=30_000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the entire page instead of only the viewport.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window during capture.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        config = CaptureConfig(
            url=args.url,
            width=args.width,
            height=args.height,
            timeout_ms=args.timeout,
            output_dir=args.output_dir,
            full_page=args.full_page,
            headless=not args.headed,
        )

        result = capture_website(config)
        print("\nCapture completed successfully.")
        print(f"Page title : {result.title}")
        print(f"Screenshot : {result.screenshot_path}")
        print(f"HTTP status: {result.status_code}")

    except (ValueError, PlaywrightError, OSError) as exc:
        LOGGER.error("Capture unsuccessful: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
