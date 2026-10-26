from pathlib import Path

import pytest

from repair_engine.self_heal import apply_css_patch


def test_css_patch_fixes_local_overflow_and_saves_screenshot(tmp_path):
    html_path = tmp_path / "checkout.html"
    screenshot_path = tmp_path / "checkout_after_fix.png"

    html_path.write_text(
        "<html><body><div style='width: 400px'>Checkout</div></body></html>",
        encoding="utf-8",
    )

    result = apply_css_patch(
        html_path=html_path,
        css_patch="div { width: 100% !important; }",
        screenshot_path=screenshot_path,
        viewport={"width": 320, "height": 720},
    )

    assert result["status"] == "css_applied"
    assert result["source_code_modified"] is False
    assert result["horizontal_overflow"] is False
    assert screenshot_path.is_file()
    assert (tmp_path / "self_heal_report.json").is_file()


def test_empty_css_patch_is_rejected(tmp_path):
    html_path = tmp_path / "checkout.html"
    html_path.write_text(
        "<html><body>Test</body></html>",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty"):
        apply_css_patch(html_path, "", tmp_path / "after.png")
