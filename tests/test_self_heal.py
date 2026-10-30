from unittest.mock import patch

from repair_engine import self_heal
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

def test_source_patch_creates_backup_and_modifies_css(tmp_path):
    source = tmp_path / "App.css"
    backup = tmp_path / "App.css.backup"
    original = "body { margin: 0; }\n"

    source.write_text(original, encoding="utf-8")

    with (
        patch.object(self_heal, "APP_CSS_PATH", source),
        patch.object(self_heal, "BACKUP_CSS_PATH", backup),
        patch.object(self_heal, "ARTIFACTS_DIR", tmp_path),
    ):
        result = self_heal.apply_source_patch(
            ".checkout { max-width: 100%; }"
        )

    assert result["status"] == "source_patched"
    assert backup.read_text(encoding="utf-8") == original
    assert ".checkout { max-width: 100%; }" in source.read_text(
        encoding="utf-8"
    )


def test_source_patch_can_be_rolled_back(tmp_path):
    source = tmp_path / "App.css"
    backup = tmp_path / "App.css.backup"
    original = "body { margin: 0; }\n"

    source.write_text(original, encoding="utf-8")
    backup.write_text(original, encoding="utf-8")

    with (
        patch.object(self_heal, "APP_CSS_PATH", source),
        patch.object(self_heal, "BACKUP_CSS_PATH", backup),
    ):
        self_heal.rollback_source_patch()

    assert source.read_text(encoding="utf-8") == original


def test_source_patch_rejects_empty_css():
    with pytest.raises(ValueError, match="non-empty"):
        self_heal.apply_source_patch("")
def test_source_verification_keeps_patch_when_build_passes(tmp_path):
    from unittest.mock import Mock, patch
    from repair_engine import source_verifier

    patch_result = {
        "status": "source_patched",
        "source_file": str(tmp_path / "App.css"),
    }

    successful_build = Mock(returncode=0, stderr="")

    with (
        patch.object(
            source_verifier, "apply_source_patch",
            return_value=patch_result,
        ),
        patch.object(
            source_verifier.subprocess, "run",
            return_value=successful_build,
        ),
        patch.object(source_verifier, "rollback_source_patch") as rollback,
    ):
        result = source_verifier.verify_source_patch(
            ".checkout { max-width: 100%; }"
        )

    assert result["status"] == "verified"
    assert result["verification_status"] == "build_passed"
    assert result["source_code_modified"] is True
    rollback.assert_not_called()


def test_source_verification_rolls_back_when_build_fails():
    from unittest.mock import Mock, patch
    from repair_engine import source_verifier

    patch_result = {
        "status": "source_patched",
        "source_file": "mock-store/src/App.css",
    }

    failed_build = Mock(
        returncode=1,
        stderr="Build failed",
    )

    with (
        patch.object(
            source_verifier, "apply_source_patch",
            return_value=patch_result,
        ),
        patch.object(
            source_verifier.subprocess, "run",
            return_value=failed_build,
        ),
        patch.object(source_verifier, "rollback_source_patch") as rollback,
    ):
        result = source_verifier.verify_source_patch(
            ".checkout { invalid-property: value; }"
        )

    assert result["status"] == "rolled_back"
    assert result["verification_status"] == "build_failed"
    assert result["source_code_modified"] is False
    rollback.assert_called_once()
def test_source_verifier_reports_build_success():
    from unittest.mock import Mock, patch
    from repair_engine import source_verifier

    patch_result = {
        "status": "source_patched",
        "source_file": "mock-store/src/App.css",
    }

    with (
        patch.object(
            source_verifier,
            "apply_source_patch",
            return_value=patch_result,
        ),
        patch.object(
            source_verifier.subprocess,
            "run",
            return_value=Mock(returncode=0, stderr=""),
        ),
        patch.object(source_verifier, "rollback_source_patch") as rollback,
    ):
        result = source_verifier.verify_source_patch(
            ".checkout { max-width: 100%; }"
        )

    assert result["verification_status"] == "build_passed"
    assert result["source_code_modified"] is True
    rollback.assert_not_called()


def test_source_verifier_rolls_back_on_build_failure():
    from unittest.mock import Mock, patch
    from repair_engine import source_verifier

    patch_result = {
        "status": "source_patched",
        "source_file": "mock-store/src/App.css",
    }

    with (
        patch.object(
            source_verifier,
            "apply_source_patch",
            return_value=patch_result,
        ),
        patch.object(
            source_verifier.subprocess,
            "run",
            return_value=Mock(returncode=1, stderr="Build error"),
        ),
        patch.object(source_verifier, "rollback_source_patch") as rollback,
    ):
        result = source_verifier.verify_source_patch(
            ".checkout { max-width: 100%; }"
        )

    assert result["verification_status"] == "build_failed"
    assert result["source_code_modified"] is False
    rollback.assert_called_once()