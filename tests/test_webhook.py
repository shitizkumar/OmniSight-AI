
from fastapi.testclient import TestClient

from backend.webhook import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_failed_build_requires_inspection():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-001",
            "project": "OmniSight-AI",
            "build_status": "failed",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.json()["inspection_required"] is True


def test_successful_build_does_not_require_inspection():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-002",
            "project": "OmniSight-AI",
            "build_status": "success",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.json()["inspection_required"] is False


def test_invalid_build_status_is_rejected():
    response = client.post(
        "/webhook/build",
        json={
            "event_id": "build-003",
            "project": "OmniSight-AI",
            "build_status": "unknown",
            "build_url": "http://localhost:5173",
        },
    )

    assert response.status_code == 422
