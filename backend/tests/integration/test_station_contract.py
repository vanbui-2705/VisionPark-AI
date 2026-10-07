from io import BytesIO
from uuid import uuid4

from PIL import Image
from sqlalchemy import func, select

from app.modules.alpr.models import Detection
from app.modules.audit_logs.models import AuditLog
from app.modules.checkin.models import ParkingTransaction


def test_preview_final_confirm_and_retry(client, db_session, operator_headers):
    lanes = client.get("/api/v1/lanes/active", headers=operator_headers)
    assert lanes.status_code == 200
    lane = next(row for row in lanes.json() if row["direction"] == "IN")
    image = BytesIO()
    Image.new("RGB", (640, 480), "white").save(image, "JPEG")
    upload = {"image": ("frame.jpg", image.getvalue(), "image/jpeg")}
    for _ in range(3):
        preview = client.post(
            "/api/v1/alpr/detections",
            headers=operator_headers,
            files=upload,
            data={"lane_id": lane["id"], "persist": "false"},
        )
        assert preview.status_code == 200
        assert preview.json()["detection_id"] is None
        assert preview.json()["provider"] == "mock"
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 0
    capture_id = str(uuid4())
    final = client.post(
        "/api/v1/alpr/detections",
        headers=operator_headers,
        files=upload,
        data={"lane_id": lane["id"], "mode": "final", "capture_id": capture_id},
    )
    assert final.status_code == 200
    detection_id = final.json()["detection_id"]
    assert detection_id == capture_id
    repeated = client.post(
        "/api/v1/alpr/detections",
        headers=operator_headers,
        files=upload,
        data={"lane_id": lane["id"], "mode": "final", "capture_id": capture_id},
    )
    assert repeated.status_code == 200
    assert repeated.json()["detection_id"] == detection_id
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 1
    other_image = BytesIO()
    Image.new("RGB", (640, 480), "red").save(other_image, "JPEG")
    conflict = client.post(
        "/api/v1/alpr/detections",
        headers=operator_headers,
        files={"image": ("other.jpg", other_image.getvalue(), "image/jpeg")},
        data={"lane_id": lane["id"], "mode": "final", "capture_id": capture_id},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "CAPTURE_ID_REUSED"
    detail = client.get(f"/api/v1/alpr/detections/{detection_id}", headers=operator_headers)
    assert detail.status_code == 200
    assert detail.json()["model_version"] == final.json()["model_version"]
    assert (
        detail.json()["actor_id"]
        == client.get("/api/v1/auth/me", headers=operator_headers).json()["id"]
    )
    path = f"/api/v1/alpr/detections/{detection_id}/confirm"
    headers = {**operator_headers, "Idempotency-Key": "station-confirm"}
    payload = {"confirmed_plate": "30F-123.45", "check_in": True}
    first = client.post(path, json=payload, headers=headers)
    assert first.status_code == 200, first.text
    transaction = first.json()["transaction"]
    assert transaction["status"] == "PARKED"
    assert transaction["source"] == "OPERATOR_CORRECTED"
    assert transaction["detection_id"] == detection_id
    replay = client.post(path, json=payload, headers=headers)
    assert replay.json()["transaction"]["id"] == transaction["id"]
    assert db_session.scalar(select(func.count()).select_from(ParkingTransaction)) == 1
    assert db_session.scalar(select(func.count()).select_from(AuditLog)) == 2
    changed = client.post(path, json={**payload, "confirmed_plate": "30F12346"}, headers=headers)
    assert changed.status_code == 409
    detail = client.get(f"/api/v1/alpr/detections/{detection_id}", headers=operator_headers).json()
    assert detail["confirmed_plate"] == "30F12345"
    assert detail["confirmed_at"] is not None
    assert detail["requires_confirmation"] is False
    assert (
        len(
            client.get(
                "/api/v1/alpr/detections?q=12345&status=CORRECTED", headers=operator_headers
            ).json()
        )
        == 1
    )
    assert client.get(f"/api/v1/alpr/detections/{detection_id}").status_code == 401


def test_failed_checkin_does_not_confirm_detection(client, db_session, operator_headers):
    lane = next(
        row
        for row in client.get("/api/v1/lanes/", headers=operator_headers).json()
        if row["direction"] == "OUT"
    )
    from uuid import uuid4

    detection = Detection(
        id=uuid4(),
        lane_id=lane["id"],
        image_key="frame.jpg",
        raw_plate="29A12345",
        normalized_plate="29A12345",
    )
    # SQLAlchemy UUID columns expect UUID objects.
    from uuid import UUID

    detection.lane_id = UUID(lane["id"])
    db_session.add(detection)
    db_session.commit()
    response = client.post(
        f"/api/v1/alpr/detections/{detection.id}/confirm",
        json={"confirmed_plate": "29A12345", "check_in": True},
        headers={**operator_headers, "Idempotency-Key": "invalid-lane"},
    )
    assert response.status_code == 400
    db_session.refresh(detection)
    assert detection.is_confirmed is False
    assert db_session.scalar(select(func.count()).select_from(AuditLog)) == 0
