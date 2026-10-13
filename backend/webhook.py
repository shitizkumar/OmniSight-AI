
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="OmniSight-AI Webhook",
    description="Receives simulated CI/CD build events.",
    version="1.0.0",
)


class BuildEvent(BaseModel):
    event_id: str = Field(min_length=1)
    project: str = Field(min_length=1)
    build_status: Literal["success", "failed"]
    build_url: str = Field(min_length=1)


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
