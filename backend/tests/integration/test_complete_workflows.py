from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy import select

from app.modules.alpr.models import Detection
from app.modules.operations.models import Notification


def test_preferences_profile_and_revocation(client, operator_headers, admin_token):
    headers = operator_headers
    assert (
        client.put(
            "/api/v1/auth/preferences", headers=headers, json={"theme": "dark", "language": "en"}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/preferences", headers=headers).json() == {
        "theme": "dark",
        "language": "en",
    }
    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"display_name": "Real operator", "email": "operator@example.test"},
    )
    assert updated.status_code == 200, updated.text
    user_id = updated.json()["id"]
    revoked = client.post(
        f"/api/v1/users/{user_id}/revoke-sessions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert revoked.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"username": "operator", "password": "operator-test-password"}
    )
    assert login.status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
        ).json()["display_name"]
        == "Real operator"
    )


def test_password_change_revokes_old_tokens(client, operator_headers):
    bad = client.post(
        "/api/v1/auth/change-password",
        headers=operator_headers,
        json={"current_password": "wrong", "new_password": "another-password"},
    )
    assert bad.status_code == 422
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=operator_headers,
        json={"current_password": "operator-test-password", "new_password": "another-password"},
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=operator_headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "operator", "password": "another-password"}
        ).status_code
        == 200
    )


def test_error_notification_persistence_and_permissions(
    client, db_session, operator_headers, admin_token
):
    correlation = str(uuid4())
    result = client.post(
        "/api/v1/errors",
        headers=operator_headers,
        json={
            "code": "NETWORK_ERROR",
            "status": 0,
            "source": "api",
            "correlation_id": correlation,
        },
    )
    assert result.status_code == 201
    retried = client.post(
        "/api/v1/errors",
        headers=operator_headers,
        json={
            "code": "NETWORK_ERROR",
            "status": 0,
            "source": "api",
            "correlation_id": correlation,
        },
    )
    assert retried.json()["id"] == result.json()["id"]
    assert client.get("/api/v1/errors", headers=operator_headers).status_code == 403
    errors = client.get("/api/v1/errors", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert errors["total"] == 1
    assert errors["items"][0]["message"] == "Request failed (NETWORK_ERROR)."
    notification = client.get("/api/v1/notifications", headers=operator_headers).json()["items"][0]
    assert not notification["read"]
    path = f"/api/v1/notifications/{notification['id']}/read"
    assert client.post(path, headers={"Authorization": f"Bearer {admin_token}"}).status_code == 404
    assert client.post(path, headers=operator_headers).status_code == 200
    assert client.get("/api/v1/notifications", headers=operator_headers).json()["items"][0]["read"]
    assert db_session.scalar(select(Notification)).read_at is not None
    assert (
        client.post(
            "/api/v1/errors",
            headers=operator_headers,
            json={"code": "BAD", "status": 500, "source": "api", "message": "secret"},
        )
        .json()
        .get("id")
        is not None
    )
    for _ in range(8):
        client.post("/api/v1/errors", headers=operator_headers, json={"code": "BAD", "status": 500})
    assert (
        client.post(
            "/api/v1/errors", headers=operator_headers, json={"code": "BAD", "status": 500}
        ).status_code
        == 429
    )


def test_saved_input_metadata_and_pagination(client, db_session, operator_headers):
    lane = next(
        lane_item
        for lane_item in client.get("/api/v1/lanes/active", headers=operator_headers).json()
        if lane_item["direction"] == "IN"
    )
    image = BytesIO()
    Image.new("RGB", (640, 480), "white").save(image, "PNG")
    capture = str(uuid4())
    data = {
        "lane_id": lane["id"],
        "mode": "final",
        "capture_id": capture,
        "input_kind": "IMAGE_UPLOAD",
    }
    files = {"image": ("image.png", image.getvalue(), "image/png")}
    saved = client.post("/api/v1/alpr/detections", headers=operator_headers, data=data, files=files)
    assert saved.status_code == 200, saved.text
    detail = client.get(f"/api/v1/alpr/detections/{capture}", headers=operator_headers).json()
    assert detail["input_kind"] == "IMAGE_UPLOAD"
    assert detail["lane_name"] == lane["name"]
    assert detail["detector_confidence"] is not None
    persisted = db_session.get(Detection, UUID(capture))
    assert persisted.image_content_type == "image/png"
    assert persisted.image_size_bytes == len(image.getvalue())
    retry = client.post("/api/v1/alpr/detections", headers=operator_headers, data=data, files=files)
    assert retry.json()["actor_id"] == saved.json()["actor_id"]
    for i in range(205):
        db_session.add(
            Detection(
                lane_id=UUID(lane["id"]),
                image_key="test-only",
                normalized_plate=f"30F{i:05}",
                confidence=0.9,
                requires_confirmation=False,
                is_confirmed=False,
                input_kind="VIDEO_FRAME",
            )
        )
    db_session.commit()
    response = client.get(
        "/api/v1/alpr/detections?paginated=true&input_kind=VIDEO_FRAME&skip=200&limit=20",
        headers=operator_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 205
    assert len(response.json()["items"]) == 5
    searched = client.get(
        "/api/v1/alpr/detections?paginated=true&q=30F00204", headers=operator_headers
    ).json()
    assert searched["total"] == 1
    assert searched["items"][0]["normalized_plate"] == "30F00204"


def test_mismatched_image_type_is_rejected(client, operator_headers):
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, "PNG")
    result = client.post(
        "/api/v1/alpr/detections",
        headers=operator_headers,
        data={"lane_id": str(uuid4())},
        files={"image": ("disguised.jpg", image.getvalue(), "image/jpeg")},
    )
    assert result.status_code == 422
    assert result.json()["code"] == "INVALID_FORMAT"


def test_selected_backend_error_is_persisted_without_sensitive_message(client, admin_token):
    from app.core.errors import AppError
    from app.modules.auth.dependencies import CurrentUser

    def failing_operation(user: CurrentUser):
        raise AppError(code="STORAGE_FAILURE", status_code=503, message="password=secret")

    client.app.add_api_route("/test/backend-failure", failing_operation, methods=["POST"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/test/backend-failure", headers=headers)
    assert response.status_code == 503
    stored = client.get("/api/v1/errors", headers=headers).json()["items"]
    assert len(stored) == 1
    assert stored[0]["source"] == "backend"
    assert stored[0]["correlationId"] == response.headers["X-Correlation-ID"]
    assert "secret" not in stored[0]["message"]


def test_manual_source_and_historical_names_are_preserved(client, db_session, operator_headers):
    from app.modules.lanes.models import Lane

    lane = next(
        row
        for row in client.get("/api/v1/lanes/active", headers=operator_headers).json()
        if row["direction"] == "IN"
    )
    response = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": str(uuid4())},
        json={
            "lane_id": lane["id"],
            "license_plate": "99Z98765",
            "source": "AI_ACCEPTED",
            "confidence": 0.99,
            "original_ai_plate": "99Z98765",
        },
    )
    assert response.status_code == 201, response.text
    transaction = response.json()["transaction"]
    assert transaction["source"] == "MANUAL_ENTRY"
    assert transaction["confidence"] is None
    assert transaction["original_ai_plate"] is None
    row = db_session.get(Lane, UUID(lane["id"]))
    row.name = "Renamed lane"
    db_session.commit()
    detail = client.get(
        "/api/v1/parking/transactions/" + transaction["id"], headers=operator_headers
    ).json()
    assert detail["lane_name"] == lane["name"]


def test_slow_inference_does_not_block_liveness(client, operator_headers, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from types import SimpleNamespace

    from app.alpr.schema import ALPRResult

    entered, release = Event(), Event()

    def process(*args, **kwargs):
        entered.set()
        release.wait(10)
        return ALPRResult(processing_time_ms=0, requires_confirmation=True)

    monkeypatch.setattr(
        "app.api.v1.endpoints.alpr.get_alpr_service",
        lambda: SimpleNamespace(process_detection=process),
    )
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, "JPEG")
    with ThreadPoolExecutor(max_workers=2) as pool:
        request = pool.submit(
            client.post,
            "/api/v1/alpr/detections",
            headers=operator_headers,
            data={"lane_id": str(uuid4()), "mode": "preview"},
            files={"image": ("frame.jpg", image.getvalue(), "image/jpeg")},
        )
        assert entered.wait(5)
        try:
            assert pool.submit(client.get, "/health/live").result(timeout=3).status_code == 200
        finally:
            release.set()
        assert request.result().status_code == 200
