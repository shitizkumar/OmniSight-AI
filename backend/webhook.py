
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"

BROWSER_REPORT = ARTIFACTS_DIR / "browser_verification_report.json"
INSPECTION_REPORT = ARTIFACTS_DIR / "ui_inspection_report.json"
RECOMMENDATION_REPORT = ARTIFACTS_DIR / "repair_recommendations.json"
DECISION_REPORT = ARTIFACTS_DIR / "qa_decision.json"

app = FastAPI(
    title="OmniSight-AI Webhook",
    description="CI/CD events and QA dashboard API.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class BuildEvent(BaseModel):
    event_id: str = Field(min_length=1)
    project: str = Field(min_length=1)
    build_status: Literal["success", "failed"]
    build_url: str = Field(min_length=1)


class QADecision(BaseModel):
    run_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]


def read_report(path: Path) -> dict:
    if not path.is_file():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read {path.name}.",
        ) from exc


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/webhook/build")
def receive_build_event(event: BuildEvent):
    return {
        "message": "Build event received",
        "event_id": event.event_id,
        "project": event.project,
        "build_status": event.build_status,
        "inspection_required": event.build_status == "failed",
    }


@app.get("/api/qa/reports")
def get_qa_reports():
    return {
        "browser": read_report(BROWSER_REPORT),
        "inspection": read_report(INSPECTION_REPORT),
        "recommendations": read_report(RECOMMENDATION_REPORT),
        "decision": read_report(DECISION_REPORT),
    }


@app.post("/api/qa/decision")
def save_qa_decision(payload: QADecision):
    browser_report = read_report(BROWSER_REPORT)

    if not browser_report:
        raise HTTPException(
            status_code=404,
            detail="Browser verification report not found.",
        )

    if browser_report.get("run_id") != payload.run_id:
        raise HTTPException(
            status_code=409,
            detail="Decision rejected: browser report is stale.",
        )

    result = {
        "run_id": payload.run_id,
        "decision": payload.decision,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_REPORT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return {
        "message": "QA decision saved.",
        **result,
    }
