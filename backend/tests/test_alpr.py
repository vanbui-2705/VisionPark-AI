from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import cv2
import numpy as np
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
from app.alpr.runtime_adapter import UnavailableRuntime
from app.core.readiness import ReadinessStatus, RuntimeALPRProbe
from app.database.session import get_database_readiness
from app.di_container import get_alpr_service
from app.modules.alpr.models import Detection
from app.modules.lanes.models import Lane


@pytest.fixture
def jpeg():
    ok, data = cv2.imencode(".jpg", np.zeros((10, 20, 3), dtype=np.uint8))
    assert ok
    return data.tobytes()


@pytest.fixture
def lane_id(db_session):
    return str(db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01")).id)


def detect(client, headers, lane_id, jpeg, mime="image/jpeg"):
    return client.post(
        "/api/v1/alpr/detections",
        headers=headers,
        data={"lane_id": lane_id},
        files={"image": ("frame.jpg", jpeg, mime)},
    )


def test_operator_login_lane_detection_persistence(
    client, operator_headers, jpeg, db_session, settings
):
    lanes = client.get("/api/v1/lanes/", headers=operator_headers)
    assert lanes.status_code == 200
    lane_id = lanes.json()[0]["id"]
    for path in ["/api/v1/lanes/active", f"/api/v1/lanes/{lane_id}"]:
        assert client.get(path, headers=operator_headers).status_code == 200
    response = detect(client, operator_headers, lane_id, jpeg)
    assert response.status_code == 200, response.text
    assert response.json()["normalized_plate"] == "29A12345"
    assert response.json()["model_version"] == "mock-alpr-0.1.0"
    row = db_session.scalar(select(Detection))
    assert str(row.lane_id) == lane_id
    assert row.normalized_plate == "29A12345"
    assert (Path(settings.local_storage_path) / lane_id / row.image_key).read_bytes() == jpeg
    ready = client.get("/health/ready").json()
    assert ready["alpr"]["version"] == response.json()["model_version"]


@pytest.mark.parametrize(
    "mime,data", [("text/plain", b"text"), ("image/jpeg", b"corrupt"), ("image/jpeg", b"")]
)
def test_invalid_image(client, operator_headers, lane_id, mime, data):
    response = detect(client, operator_headers, lane_id, data, mime)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_upload_limit_uses_settings(client, operator_headers, lane_id, jpeg, settings):
    settings.upload_max_bytes = 5
    assert detect(client, operator_headers, lane_id, jpeg).status_code == 422


def test_missing_and_invalid_lane_id(client, operator_headers, jpeg):
    response = client.post(
        "/api/v1/alpr/detections",
        headers=operator_headers,
        files={"image": ("frame.jpg", jpeg, "image/jpeg")},
    )
    assert response.status_code == 422
    assert detect(client, operator_headers, "not-a-uuid", jpeg).status_code == 422


@pytest.mark.parametrize("inactive", [False, True])
def test_missing_or_inactive_lane(client, operator_headers, db_session, jpeg, inactive):
    lane = db_session.scalar(select(Lane))
    lane.is_active = False
    db_session.commit()
    lane_id = str(lane.id) if inactive else str(uuid4())
    assert detect(client, operator_headers, lane_id, jpeg).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 0


def test_detection_requires_authentication(client, lane_id, jpeg):
    assert detect(client, {}, lane_id, jpeg).status_code == 401


@pytest.mark.parametrize("error", [TimeoutError(), ALPRNotReadyError(), ALPRProcessingError()])
def test_runtime_failure(client, operator_headers, lane_id, jpeg, error):
    service = MagicMock()
    service.process_detection.side_effect = error
    client.app.dependency_overrides[get_alpr_service] = lambda: service
    response = detect(client, operator_headers, lane_id, jpeg)
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"


def test_failed_record_rolls_back_and_cleans_file(
    client, operator_headers, lane_id, jpeg, db_session, settings, monkeypatch
):
    def fail_commit(self):
        raise SQLAlchemyError("simulated database failure")

    from sqlalchemy.orm import Session

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = detect(client, operator_headers, lane_id, jpeg)
    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"
    assert list(Path(settings.local_storage_path).rglob("*.jpg")) == []
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 0


def test_unavailable_runtime_shared_by_health_and_detection(
    client, operator_headers, lane_id, jpeg
):
    runtime = UnavailableRuntime()
    client.app.state.alpr_runtime = runtime
    client.app.state.alpr_readiness_probe = RuntimeALPRProbe(
        runtime, provider="onnx", version=runtime.version
    )
    for path in ["/health/ready", "/api/v1/alpr/health/ready"]:
        assert client.get(path).status_code == 503
    assert detect(client, operator_headers, lane_id, jpeg).status_code == 503


def test_health_aliases_check_database(client):
    client.app.dependency_overrides[get_database_readiness] = lambda: ReadinessStatus(
        False, "offline"
    )
    for path in ["/health/ready", "/api/v1/alpr/health/ready"]:
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()["database"]["status"] == "not_ready"
    assert client.get("/api/v1/alpr/health/live").status_code == 200
