import base64
import json
import os
from pathlib import Path

import httpx


def analyze_ui(screenshot_path: Path, html_path: Path) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_VISION_MODEL")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. VLM analysis was not run."
        )
    if not model:
        raise RuntimeError(
            "Set OPENAI_VISION_MODEL to a vision-capable model."
        )
    if not screenshot_path.is_file() or not html_path.is_file():
        raise FileNotFoundError("Screenshot or HTML snapshot not found.")

    image_data = base64.b64encode(
        screenshot_path.read_bytes()
    ).decode("ascii")
    html = html_path.read_text(encoding="utf-8")[:20000]

    prompt = f"""
Analyze the checkout screenshot and HTML for visible layout,
overlap, clipping, contrast, and accessibility issues.
Report only evidence-supported issues.
Return JSON with a defects list. Each defect must include:
element, issue, severity, evidence, suggested_fix.

HTML snapshot:
{html}
"""

    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": "data:image/png;base64," + image_data,
                        "detail": "high",
                    },
                ],
            }],
            "text": {"format": {"type": "json_object"}},
        },
        timeout=90.0,
    )
    response.raise_for_status()
    payload = response.json()

    output_text = "".join(
        content.get("text", "")
        for item in payload.get("output", [])
        if item.get("type") == "message"
        for content in item.get("content", [])
        if content.get("type") == "output_text"
    )
    result = json.loads(output_text)
    defects = result.get("defects")

    if not isinstance(defects, list):
        raise ValueError("VLM response must contain a defects list.")

    return {
        "inspection_status": "completed",
        "inspection_method": "openai_vlm",
        "ai_vision_used": True,
        "defects_found": len(defects),
        "defects": defects,
    }
