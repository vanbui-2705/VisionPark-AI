from uuid import uuid4

from sqlalchemy import select

from app.modules.alpr.models import Detection
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane, LaneDirection


def get_in_lane(db_session):
    return db_session.scalar(select(Lane).where(Lane.direction == LaneDirection.IN))


def test_checkin_creates_parked_transaction_and_audit(client, db_session, operator_headers):
    lane = get_in_lane(db_session)
    response = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "29A-123.45"},
        headers={**operator_headers, "Idempotency-Key": "checkin-1"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["transaction"]["license_plate"] == "29A12345"
    assert body["transaction"]["status"] == "PARKED"
    assert body["transaction"]["source"] == "MANUAL_ENTRY"

    history = client.get("/api/v1/parking/transactions?q=29A12345", headers=operator_headers)
    assert history.status_code == 200
    assert len(history.json()["data"]) == 1

    audit = client.get("/api/v1/audit-logs/?action=CREATE_CHECKIN", headers=operator_headers)
    assert audit.status_code == 200
    assert audit.json()["data"][0]["resource"] == "ParkingTransaction"


def test_checkin_idempotency_returns_same_transaction_and_rejects_changed_payload(
    client, db_session, operator_headers
):
    lane = get_in_lane(db_session)
    headers = {**operator_headers, "Idempotency-Key": "same-key"}
    payload = {"lane_id": str(lane.id), "license_plate": "51F 888.88"}

    first = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    second = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    changed = client.post(
        "/api/v1/parking/check-in",
        json={**payload, "license_plate": "30A12345"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["transaction"]["id"] == first.json()["transaction"]["id"]
    assert changed.status_code == 409
    assert changed.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_duplicate_active_plate_is_rejected(client, db_session, operator_headers):
    lane = get_in_lane(db_session)
    base = {"lane_id": str(lane.id), "license_plate": "30B-999.99"}
    first = client.post(
        "/api/v1/parking/check-in",
        json=base,
        headers={**operator_headers, "Idempotency-Key": "duplicate-1"},
    )
    duplicate = client.post(
        "/api/v1/parking/check-in",
        json=base,
        headers={**operator_headers, "Idempotency-Key": "duplicate-2"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "PLATE_ALREADY_PARKED"


def test_checkin_sources_and_lane_validation(client, db_session, operator_headers):
    in_lane = get_in_lane(db_session)
    out_lane = db_session.scalar(select(Lane).where(Lane.direction == LaneDirection.OUT))
    detection = Detection(
        id=uuid4(),
        lane_id=in_lane.id,
        image_key="lane_capture.jpg",
        raw_plate="29A-123.45",
        normalized_plate="29A12345",
        confidence=0.97,
    )
    db_session.add(detection)
    db_session.commit()

    accepted = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": str(in_lane.id),
            "license_plate": "29A12345",
            "detection_id": str(detection.id),
        },
        headers={**operator_headers, "Idempotency-Key": "source-ai"},
    )
    corrected = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": str(in_lane.id),
            "license_plate": "29A12346",
            "detection_id": str(detection.id),
            "override_reason": "Operator corrected one character",
        },
        headers={**operator_headers, "Idempotency-Key": "source-corrected"},
    )
    invalid_direction = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(out_lane.id), "license_plate": "60A12345"},
        headers={**operator_headers, "Idempotency-Key": "source-out"},
    )

    assert accepted.status_code == 201
    assert accepted.json()["transaction"]["source"] == "AI_ACCEPTED"
    assert corrected.status_code == 201
    assert corrected.json()["transaction"]["source"] == "OPERATOR_CORRECTED"
    assert invalid_direction.status_code == 400
    assert invalid_direction.json()["code"] == "INVALID_LANE_TYPE"

    parked = db_session.scalar(
        select(ParkingTransaction).where(ParkingTransaction.status == TransactionStatus.PARKED)
    )
    assert parked is not None


def test_checkin_requires_auth_and_rejects_inactive_lane(client, db_session, operator_headers):
    lane = get_in_lane(db_session)
    unauthenticated = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "70A12345"},
        headers={"Idempotency-Key": "auth-required"},
    )

    lane.is_active = False
    db_session.commit()
    inactive = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "70A12345"},
        headers={**operator_headers, "Idempotency-Key": "inactive-lane"},
    )

    assert unauthenticated.status_code == 401
    assert inactive.status_code == 400
    assert inactive.json()["code"] == "LANE_INACTIVE"
