import json

import pytest

from vision_engine.vlm_client import analyze_ui


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def make_payload(result):
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(result),
                    }
                ],
            }
        ]
    }


def test_analyze_ui_parses_mocked_vlm_response(tmp_path, monkeypatch):
    screenshot = tmp_path / "screen.png"
    html = tmp_path / "checkout.html"
    screenshot.write_bytes(b"fake-image-data")
    html.write_text("<html><body>Checkout</body></html>", encoding="utf-8")

    monkeypatch.setenv("VLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_VISION_MODEL", "test-vision-model")

    defect = {
        "element": "page_layout",
        "issue": "Horizontal overflow detected.",
        "severity": "high",
        "evidence": "Document width exceeds viewport width.",
        "suggested_fix": "Use responsive widths.",
    }

    def fake_post(url, **kwargs):
        assert url == "https://api.openai.com/v1/responses"
        assert kwargs["json"]["model"] == "test-vision-model"
        return FakeResponse(make_payload({"defects": [defect]}))

    monkeypatch.setattr("vision_engine.vlm_client.httpx.post", fake_post)

    result = analyze_ui(screenshot, html)

    assert result["inspection_status"] == "completed"
    assert result["inspection_method"] == "openai_vlm"
    assert result["ai_vision_used"] is True
    assert result["defects_found"] == 1
    assert result["defects"] == [defect]


def test_analyze_ui_rejects_invalid_defects_field(tmp_path, monkeypatch):
    screenshot = tmp_path / "screen.png"
    html = tmp_path / "checkout.html"
    screenshot.write_bytes(b"fake-image-data")
    html.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setenv("VLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_VISION_MODEL", "test-vision-model")

    monkeypatch.setattr(
        "vision_engine.vlm_client.httpx.post",
        lambda *args, **kwargs: FakeResponse(
            make_payload({"defects": "no defects"})
        ),
    )

    with pytest.raises(ValueError, match="defects list"):
        analyze_ui(screenshot, html)


def test_analyze_ui_requires_api_key(tmp_path, monkeypatch):
    screenshot = tmp_path / "screen.png"
    html = tmp_path / "checkout.html"
    screenshot.write_bytes(b"fake-image-data")
    html.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setenv("VLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_VISION_MODEL", "test-vision-model")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is missing"):
        analyze_ui(screenshot, html)

