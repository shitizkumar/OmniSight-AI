import base64
import json
import os
from pathlib import Path

import httpx


PROVIDERS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/responses",
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_VISION_MODEL",
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/responses",
        "key_env": "XAI_API_KEY",
        "model_env": "XAI_VISION_MODEL",
    },
}


def analyze_ui(screenshot_path: Path, html_path: Path) -> dict:
    provider = os.getenv("VLM_PROVIDER", "openai").strip().lower()

    if provider not in PROVIDERS:
        raise ValueError(
            f"Unsupported VLM_PROVIDER '{provider}'. Use openai or xai."
        )

    config = PROVIDERS[provider]
    api_key = os.getenv(config["key_env"])
    model = os.getenv(config["model_env"])

    if not api_key:
        raise RuntimeError(f"{config['key_env']} is missing.")
    if not model:
        raise RuntimeError(f"Set {config['model_env']} to a vision-capable model.")
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
        config["endpoint"],
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

    if not output_text:
        raise ValueError("VLM response did not contain output text.")

    result = json.loads(output_text)
    defects = result.get("defects")

    if not isinstance(defects, list):
        raise ValueError("VLM response must contain a defects list.")

    return {
        "inspection_status": "completed",
        "inspection_method": f"{provider}_vlm",
        "ai_vision_used": True,
        "defects_found": len(defects),
        "defects": defects,
    }
