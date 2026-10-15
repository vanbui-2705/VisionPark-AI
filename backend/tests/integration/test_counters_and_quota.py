from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.checkin.counter_models import CounterEvent, ParkingCounter
from app.modules.checkin.lifecycle_models import AppendOnlyModelError
from app.modules.checkin.models import TransactionStatus
from app.modules.lanes.models import AllowedVehicleType, Lane, LaneDirection


@pytest.fixture
def operator_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "operator-test-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def in_lane(db_session: Session) -> Lane:
    lane = db_session.query(Lane).filter_by(direction=LaneDirection.IN).first()
    if not lane:
        lane = Lane(
            name="IN_LANE_GENERIC",
            direction=LaneDirection.IN,
            video_source="rtsp://dummy",
            is_active=True,
            allowed_vehicle_type=AllowedVehicleType.ALL,
        )
        db_session.add(lane)
        db_session.commit()
    return lane


def test_checkin_increments_counter_and_records_counter_event(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Check-in thành công tăng bộ đếm +1 và ghi một dòng counter_events cùng transaction."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    plate = "29A11122"
    payload = {
        "lane_id": str(in_lane.id),
        "license_plate": plate,
        "vehicle_type": "CAR",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    tx_id = response.json()["transaction"]["id"]

    # Kiểm tra parking_counters
    counter = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "CAR",
            )
        )
        .scalars()
        .one()
    )
    assert counter.occupied >= 1

    # Kiểm tra counter_events
    events = (
        db_session.execute(select(CounterEvent).where(CounterEvent.session_id == UUID(tx_id)))
        .scalars()
        .all()
    )
    assert len(events) == 1
    event = events[0]
    assert event.delta == 1
    assert event.reason == "CHECK_IN"
    assert event.vehicle_type == "CAR"


def test_checkin_denied_when_visitor_capacity_full(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Khách vãng lai bị từ chối CAPACITY_FULL khi số chỗ vượt safe_capacity - reserved_quota."""
    # CAR: safe_capacity = 100, resident_quota = 20, staff_quota = 10 -> visitor limit = 70
    counter = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "CAR",
            )
        )
        .scalars()
        .one_or_none()
    )
    if not counter:
        counter = ParkingCounter(
            building_id=in_lane.building_id,
            vehicle_type="CAR",
            occupied=70,
        )
        db_session.add(counter)
    else:
        counter.occupied = 70
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload = {
        "lane_id": str(in_lane.id),
        "license_plate": "29A33344",
        "vehicle_type": "CAR",
        "customer_class": "VISITOR",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 403, response.text
    err = response.json()
    assert err["code"] == "CAPACITY_FULL"
    assert "khách vãng lai" in err["message"].lower()


def test_checkin_resident_allowed_when_visitor_full_until_physical_capacity(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Cư dân có quota đảm bảo vẫn được vào khi khách vãng lai đã bị chặn (BR mục 4.4)."""
    counter = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "CAR",
            )
        )
        .scalars()
        .one_or_none()
    )
    if not counter:
        counter = ParkingCounter(
            building_id=in_lane.building_id,
            vehicle_type="CAR",
            occupied=75,  # Vượt visitor limit (70) nhưng < physical_capacity (120)
        )
        db_session.add(counter)
    else:
        counter.occupied = 75
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload = {
        "lane_id": str(in_lane.id),
        "license_plate": "30A55566",
        "vehicle_type": "CAR",
        "customer_class": "RESIDENT",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["transaction"]["status"] == TransactionStatus.PARKED

    # Trường hợp chạm ngưỡng physical_capacity (120 cho CAR) thì cư dân cũng bị từ chối
    counter.occupied = 120
    db_session.commit()

    headers2 = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload2 = {
        "lane_id": str(in_lane.id),
        "license_plate": "30A77788",
        "vehicle_type": "CAR",
        "customer_class": "RESIDENT",
    }
    response2 = client.post("/api/v1/parking/check-in", json=payload2, headers=headers2)
    assert response2.status_code == 403
    assert response2.json()["code"] == "CAPACITY_FULL"
    assert "vật lý tối đa" in response2.json()["message"].lower()


def test_adjust_counter_endpoint_and_events(
    client: TestClient, operator_token: str, db_session: Session
):
    """POST /api/v1/parking/counters/adjust điều chỉnh số đếm có lý do và ghi counter_events."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {
        "vehicle_type": "MOTORBIKE",
        "delta": 5,
        "reason": "PERIODIC_RECONCILIATION",
        "note": "Kiểm kê đầu giờ ca",
    }
    response = client.post("/api/v1/parking/counters/adjust", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vehicle_type"] == "MOTORBIKE"
    assert data["delta"] == 5
    assert data["reason"] == "PERIODIC_RECONCILIATION"

    # Kiểm tra counter_events
    event = (
        db_session.execute(
            select(CounterEvent)
            .where(
                CounterEvent.vehicle_type == "MOTORBIKE",
                CounterEvent.reason == "PERIODIC_RECONCILIATION",
            )
            .order_by(CounterEvent.occurred_at.desc())
        )
        .scalars()
        .first()
    )
    assert event is not None
    assert event.delta == 5
    assert event.note == "Kiểm kê đầu giờ ca"

    # Kiểm tra chặn delta khiến occupied bị âm
    negative_payload = {
        "vehicle_type": "MOTORBIKE",
        "delta": -9999,
        "reason": "INVALID_ADJUST",
    }
    res_neg = client.post("/api/v1/parking/counters/adjust", json=negative_payload, headers=headers)
    assert res_neg.status_code == 422
    assert res_neg.json()["code"] == "NEGATIVE_OCCUPIED"


def test_get_availability_endpoint(client: TestClient, operator_token: str):
    """GET /api/v1/parking/availability trả về số chỗ trống cho màn hình cổng."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    response = client.get("/api/v1/parking/availability", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()
    assert isinstance(items, list)
    types = {item["vehicle_type"] for item in items}
    assert {"CAR", "MOTORBIKE", "BICYCLE"}.issubset(types)
    for item in items:
        assert "occupied" in item
        assert "available" in item
        assert "safe_capacity" in item
        assert "physical_capacity" in item
        assert item["status"] in ("AVAILABLE", "NEARLY_FULL", "FULL")


def test_counter_events_append_only(db_session: Session):
    """Bảng counter_events chỉ thêm, cấm sửa và cấm xóa (append-only)."""
    event = CounterEvent(
        vehicle_type="CAR",
        delta=1,
        reason="TEST_APPEND_ONLY",
        actor_type="SYSTEM",
    )
    db_session.add(event)
    db_session.commit()

    # Thử sửa
    event.reason = "MODIFIED_REASON"
    with pytest.raises(
        AppendOnlyModelError, match="CounterEvent is append-only: updates are strictly forbidden."
    ):
        db_session.commit()
    db_session.rollback()

    # Thử xóa
    saved_event = db_session.get(CounterEvent, event.id)
    assert saved_event is not None
    db_session.delete(saved_event)
    with pytest.raises(
        AppendOnlyModelError, match="CounterEvent is append-only: deletions are strictly forbidden."
    ):
        db_session.commit()
    db_session.rollback()
