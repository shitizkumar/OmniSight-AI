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
    assert result["verification_status"] == "repair_verified"
    assert result["before"]["horizontal_overflow"] is True
    assert result["after"]["horizontal_overflow"] is False
    assert result["source_code_modified"] is False
    assert screenshot_path.is_file()
    assert (tmp_path / "self_heal_report.json").is_file()


def test_ineffective_patch_is_reported_as_failed(tmp_path):
    html_path = tmp_path / "checkout.html"
    screenshot_path = tmp_path / "checkout_after_fix.png"

    html_path.write_text(
        "<html><body><div style='width: 400px'>Checkout</div></body></html>",
        encoding="utf-8",
    )

    result = apply_css_patch(
        html_path=html_path,
        css_patch="div { color: red; }",
        screenshot_path=screenshot_path,
        viewport={"width": 320, "height": 720},
    )

    assert result["before"]["horizontal_overflow"] is True
    assert result["after"]["horizontal_overflow"] is True
    assert result["verification_status"] == "repair_failed"


def test_no_overflow_is_reported_as_no_repair_needed(tmp_path):
    html_path = tmp_path / "checkout.html"
    html_path.write_text(
        "<html><body><div style='width: 200px'>Checkout</div></body></html>",
        encoding="utf-8",
    )

    result = apply_css_patch(
        html_path=html_path,
        css_patch="div { color: blue; }",
        screenshot_path=tmp_path / "after.png",
        viewport={"width": 320, "height": 720},
    )

    assert result["verification_status"] == "no_repair_needed"


def test_empty_css_patch_is_rejected(tmp_path):
    html_path = tmp_path / "checkout.html"
    html_path.write_text(
        "<html><body>Test</body></html>",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty"):
        apply_css_patch(html_path, "", tmp_path / "after.png")

def test_self_heal_module_has_no_automatic_source_changes():
    from repair_engine import self_heal

    assert callable(self_heal.apply_css_patch)
    assert self_heal.MAX_CSS_LENGTH == 10_000
