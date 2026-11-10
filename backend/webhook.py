
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from github_integration.pull_request import create_pull_request

from browser_agent.website_capture import validate_public_url
from run_pipeline import run_website_pipeline
from repair_engine.self_heal import apply_approved_url_patch
from vision_engine.vlm_client import generate_css_patch
import httpx


ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
WEBSITE_RUNS_DIR = ARTIFACTS_DIR / "website_runs"
JOBS_DIR = WEBSITE_RUNS_DIR / "jobs"

BROWSER_REPORT = ARTIFACTS_DIR / "browser_verification_report.json"
INSPECTION_REPORT = ARTIFACTS_DIR / "ui_inspection_report.json"
RECOMMENDATION_REPORT = ARTIFACTS_DIR / "repair_recommendations.json"
DECISION_REPORT = ARTIFACTS_DIR / "qa_decision.json"

SCREENSHOT_FILES = {
    "mobile_small.png",
    "mobile.png",
    "tablet.png",
    "desktop.png",
    "verification_mobile_small.png",
    "verification_mobile.png",
    "verification_tablet.png",
    "verification_desktop.png",
}

app = FastAPI(
    title="OmniSight-AI Webhook",
    description="CI/CD events and website QA inspection API.",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class BuildEvent(BaseModel):
    event_id: str = Field(min_length=1)
    project: str = Field(min_length=1)
    build_status: Literal["success", "failed"]
    build_url: str = Field(min_length=1)


class WebsiteInspectionRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class QADecision(BaseModel):
    run_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]
class URLRepairRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    viewport_width: int = Field(default=320, ge=1, le=3840)
    viewport_height: int = Field(default=720, ge=1, le=2160)
class GitHubPullRequestRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    commit_message: str = Field(min_length=1, max_length=200)
    pr_title: str = Field(min_length=1, max_length=200)
    pr_body: str = Field(min_length=1, max_length=5000)


def read_report(path: Path) -> dict:
    if not path.is_file():
        return {}

    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read {path.name}.",
        ) from exc


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def job_status_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def update_job(job_id: str, **updates) -> dict:
    path = job_status_path(job_id)
    status = read_report(path)
    status.update(updates)
    write_json(path, status)
    return status


def execute_website_inspection(job_id: str, url: str) -> None:
    """Execute website inspection outside the API request."""
    update_job(
        job_id,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        result = run_website_pipeline(
            url=url,
            output_dir=WEBSITE_RUNS_DIR,
        )

        update_job(
            job_id,
            status="completed",
            run_id=result["run_id"],
            pipeline_status=result["pipeline_status"],
            report_directory=result["report_directory"],
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            error=str(exc),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )


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


@app.post("/api/qa/inspect", status_code=202)
def start_website_inspection(
    payload: WebsiteInspectionRequest,
    background_tasks: BackgroundTasks,
):
    try:
        validate_public_url(payload.url)
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    job_id = uuid.uuid4().hex

    status = {
        "job_id": job_id,
        "url": payload.url,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(job_status_path(job_id), status)

    background_tasks.add_task(
        execute_website_inspection,
        job_id,
        payload.url,
    )

    return {
        "message": "Website inspection queued.",
        **status,
    }


@app.get("/api/qa/runs/{job_id}")
def get_website_inspection(job_id: str):
    status = read_report(job_status_path(job_id))

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Inspection job not found.",
        )

    result = {"job": status, "reports": {}}

    run_id = status.get("run_id")

    if run_id:
        run_dir = WEBSITE_RUNS_DIR / run_id

        result["reports"] = {
            "capture": read_report(run_dir / "capture_report.json"),
            "inspection": read_report(
                run_dir / "ui_inspection_report.json"
            ),
            "recommendations": read_report(
                run_dir / "repair_recommendations.json"
            ),
            "verification": read_report(
                run_dir / "browser_verification_report.json"
            ),
            "decision": read_report(run_dir / "qa_decision.json"),
        }

    return result
REPAIR_PREVIEW_FILES = {
    "url_repair_before.png",
    "url_repair_after.png",
}


@app.get("/api/qa/runs/{job_id}/screenshots/{filename}")
def get_website_screenshot(job_id: str, filename: str):
    if filename not in SCREENSHOT_FILES:
        raise HTTPException(
            status_code=404,
            detail="Screenshot not found.",
        )


    status = read_report(job_status_path(job_id))
    run_id = status.get("run_id")

    if not run_id:
        raise HTTPException(
            status_code=404,
            detail="Inspection results are not available.",
        )

    screenshot_path = WEBSITE_RUNS_DIR / run_id / filename

    if not screenshot_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Screenshot file not found.",
        )

    return FileResponse(screenshot_path, media_type="image/png")


@app.get("/api/qa/runs/{job_id}/repair-preview/{filename}")
def get_repair_preview(job_id: str, filename: str):
    if filename not in REPAIR_PREVIEW_FILES:
        raise HTTPException(
            status_code=404,
            detail="Repair preview not found.",
        )

    status = read_report(job_status_path(job_id))
    run_id = status.get("run_id")

    if not run_id:
        raise HTTPException(
            status_code=404,
            detail="Inspection results are not available.",
        )

    preview_path = (
        WEBSITE_RUNS_DIR / run_id / "repair_preview" / filename
    )

    if not preview_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Repair preview image not found.",
        )

    return FileResponse(preview_path, media_type="image/png")


@app.get("/api/qa/runs/{job_id}/defect-crops/{filename}")
def get_defect_crop(job_id: str, filename: str):
    if not re.fullmatch(r"defect_\d{2}\.png", filename):
        raise HTTPException(
            status_code=404,
            detail="Defect crop not found.",
        )

    status = read_report(job_status_path(job_id))

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Inspection job not found.",
        )

    run_id = status.get("run_id")

    if not run_id:
        raise HTTPException(
            status_code=404,
            detail="Inspection results are not available.",
        )

    crop_path = WEBSITE_RUNS_DIR / run_id / "defect_crops" / filename

    if not crop_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Defect crop file not found.",
        )

    return FileResponse(crop_path, media_type="image/png")
@app.post("/api/qa/decision")
def save_qa_decision(payload: QADecision):
    website_run_dir = WEBSITE_RUNS_DIR / payload.run_id
    website_browser_report = read_report(
        website_run_dir / "browser_verification_report.json"
    )

    if website_browser_report:
        if website_browser_report.get("run_id") != payload.run_id:
            raise HTTPException(
                status_code=409,
                detail="Decision rejected: browser report is stale.",
            )

        decision_path = website_run_dir / "qa_decision.json"

    else:
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

        decision_path = DECISION_REPORT

    result = {
        "run_id": payload.run_id,
        "decision": payload.decision,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(decision_path, result)

    return {
        "message": "QA decision saved.",
        **result,
    }

@app.post("/api/qa/repair")
def repair_approved_website(payload: URLRepairRequest):
    # Validate the run ID before constructing a filesystem path.
    if (
        len(payload.run_id) > 64
        or any(char not in "0123456789abcdef-" for char in payload.run_id.lower())
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid website run ID.",
        )

    run_dir = WEBSITE_RUNS_DIR / payload.run_id

    if not run_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Website run not found.",
        )

    decision = read_report(run_dir / "qa_decision.json")

    if (
        decision.get("run_id") != payload.run_id
        or decision.get("decision") != "approved"
    ):
        raise HTTPException(
            status_code=403,
            detail="An approved QA decision is required.",
        )

    capture_report = read_report(run_dir / "capture_report.json")

    if capture_report.get("run_id") != payload.run_id:
        raise HTTPException(
            status_code=409,
            detail="Capture report is missing or belongs to another run.",
        )

    html_path = run_dir / "website.html"

    if not html_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Captured website HTML not found.",
        )

    # Require a real reported defect before applying a repair.
    inspection = read_report(run_dir / "ui_inspection_report.json")
    defects = inspection.get("defects")

    if not isinstance(defects, list) or not any(
        isinstance(defect, dict)
        and "overflow" in str(defect.get("issue", "")).lower()
        for defect in defects
    ):
        raise HTTPException(
            status_code=409,
            detail="No supported horizontal overflow defect was found.",
        )

    try:
        generated = generate_css_patch(
            html_path=html_path,
            defects=defects,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI CSS generation failed: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI CSS provider request failed.",
        ) from exc

    try:
        result = apply_approved_url_patch(
            html_path=html_path,
            css_patch=generated["css_patch"],
            output_dir=run_dir / "repair_preview",
            approved=True,
            viewport={
                "width": payload.viewport_width,
                "height": payload.viewport_height,
            },
        )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "message": "AI-generated approved repair preview completed.",
        "run_id": payload.run_id,
        "ai_repair": {
            "explanation": generated["explanation"],
            "provider": generated["provider"],
            "model": generated["model"],
            "generated_css": generated["css_patch"],
        },
        **result,
    }
@app.post("/api/qa/github/pull-request")
def create_qa_pull_request(payload: GitHubPullRequestRequest):
    if any(
        char not in "0123456789abcdef-"
        for char in payload.run_id.lower()
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid website run ID.",
        )

    run_dir = WEBSITE_RUNS_DIR / payload.run_id

    if not run_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Website run not found.",
        )

    decision = read_report(run_dir / "qa_decision.json")

    if (
        decision.get("run_id") != payload.run_id
        or decision.get("decision") != "approved"
    ):
        raise HTTPException(
            status_code=403,
            detail="An approved QA decision is required.",
        )

    report_path = run_dir / "browser_verification_report.json"

    if not report_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Browser verification report not found.",
        )

    try:
        pull_request_url = create_pull_request(
            file_path="mock-store/src/App.css",
            commit_message=payload.commit_message,
            pr_title=payload.pr_title,
            pr_body=payload.pr_body,
            expected_run_id=payload.run_id,
            report_path=report_path,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return {
        "message": "GitHub pull request created.",
        "run_id": payload.run_id,
        "pull_request_url": pull_request_url,
    }
