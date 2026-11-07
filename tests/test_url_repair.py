
import json

import pytest

from repair_engine.self_heal import apply_approved_url_patch


def test_url_repair_requires_approval(tmp_path):
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Test</body></html>")

    with pytest.raises(PermissionError):
        apply_approved_url_patch(
            html_path=html_path,
            css_patch="body { color: red; }",
            output_dir=tmp_path / "output",
            approved=False,
        )


def test_url_repair_creates_before_after_screenshots_and_report(tmp_path):
    html_path = tmp_path / "page.html"
    html_path.write_text(
        """
        <html>
            <body>
                <div style="width: 600px; height: 50px;"></div>
            </body>
        </html>
        """
    )

    output_dir = tmp_path / "output"

    result = apply_approved_url_patch(
        html_path=html_path,
        css_patch="div { width: 100% !important; }",
        output_dir=output_dir,
        approved=True,
        viewport={"width": 320, "height": 720},
    )

    assert result["status"] == "preview_completed"
    assert result["verification_status"] == "repair_verified"
    assert result["source_code_modified"] is False
    assert result["external_website_modified"] is False

    assert (output_dir / "url_repair_before.png").is_file()
    assert (output_dir / "url_repair_after.png").is_file()
    assert (output_dir / "self_heal_report.json").is_file()

    report = json.loads(
        (output_dir / "self_heal_report.json").read_text()
    )
    assert report["approved"] is True


def test_url_repair_does_not_modify_html_snapshot(tmp_path):
    html_path = tmp_path / "page.html"
    original_html = """
    <html>
        <body>
            <div style="width: 600px;"></div>
        </body>
    </html>
    """
    html_path.write_text(original_html, encoding="utf-8")

    apply_approved_url_patch(
        html_path=html_path,
        css_patch="div { width: 100% !important; }",
        output_dir=tmp_path / "output",
        approved=True,
    )

    assert html_path.read_text(encoding="utf-8") == original_html
