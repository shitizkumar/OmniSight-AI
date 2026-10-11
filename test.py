
"""Tests for the OmniSight browser capture module."""

from pathlib import Path

import pytest

from browser_agent.capture import CaptureConfig, capture_website


def test_config_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        CaptureConfig(url="file:///example.html")


def test_config_rejects_invalid_viewport() -> None:
    with pytest.raises(ValueError, match="positive"):
        CaptureConfig(width=0)


def test_capture_creates_screenshot(tmp_path: Path) -> None:
    config = CaptureConfig(
        url="https://example.com",
        width=390,
        height=844,
        output_dir=tmp_path,
    )

    result = capture_website(config)

    assert result.screenshot_path.is_file()
    assert result.screenshot_path.stat().st_size > 0
    assert result.title == "Example Domain"
    assert result.viewport == {"width": 390, "height": 844}
    assert result.status_code == 200
    assert result.captured_at
