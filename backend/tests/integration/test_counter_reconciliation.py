from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit_logs.models import AuditLog
from app.modules.checkin.counter_models import CounterEvent, ParkingCounter
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
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


def test_check_discrepancies_detects_drift_correctly(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Job đối soát phát hiện đúng sai lệch giữa số phiên PARKED thực tế và bộ đếm."""
    # 1. Tạo 3 phiên PARKED xe ô tô
    for i in range(3):
        tx = ParkingTransaction(
            license_plate=f"29A8888{i}",
            normalized_plate=f"29A8888{i}",
            vehicle_type="CAR",
            status=TransactionStatus.PARKED,
            lane_id=in_lane.id,
            building_id=in_lane.building_id,
            lane_snapshot_name=in_lane.name,
            lane_snapshot_direction=in_lane.direction,
            source="MANUAL_ENTRY",
            idempotency_key=str(uuid4()),
            request_fingerprint=uuid4().hex * 2,
        )
        db_session.add(tx)

    # 2. Giả lập bộ đếm bị lệch (chỉ ghi nhận 1 xe, lệch drift = +2)
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
            occupied=1,
        )
        db_session.add(counter)
    else:
        counter.occupied = 1
    db_session.commit()

    headers = {"Authorization": f"Bearer {operator_token}"}
    response = client.get("/api/v1/parking/counters/discrepancies", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()

    car_drift = next((item for item in items if item["vehicle_type"] == "CAR"), None)
    assert car_drift is not None
    assert car_drift["counter_occupied"] == 1
    assert car_drift["active_sessions"] >= 3
    assert car_drift["drift"] == car_drift["active_sessions"] - 1


def test_reconcile_and_adjust_updates_counter_and_records_event_and_audit(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Admin hiệu chỉnh qua counter_events kèm lý do và audit — không sửa số trực tiếp."""
    # 1. Tạo 2 phiên PARKED cho MOTORBIKE
    for i in range(2):
        tx = ParkingTransaction(
            license_plate=f"59B1112{i}",
            normalized_plate=f"59B1112{i}",
            vehicle_type="MOTORBIKE",
            status=TransactionStatus.PARKED,
            lane_id=in_lane.id,
            building_id=in_lane.building_id,
            lane_snapshot_name=in_lane.name,
            lane_snapshot_direction=in_lane.direction,
            source="MANUAL_ENTRY",
            idempotency_key=str(uuid4()),
            request_fingerprint=uuid4().hex * 2,
        )
        db_session.add(tx)

    # Giả lập bộ đếm bị lệch: occupied = 0 (drift = +2)
    counter = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "MOTORBIKE",
            )
        )
        .scalars()
        .one_or_none()
    )
    if not counter:
        counter = ParkingCounter(
            building_id=in_lane.building_id,
            vehicle_type="MOTORBIKE",
            occupied=0,
        )
        db_session.add(counter)
    else:
        counter.occupied = 0
    db_session.commit()

    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {
        "auto_correct": True,
        "reason": "PERIODIC_AUDIT_NIGHTLY",
    }
    response = client.post("/api/v1/parking/counters/reconcile", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["has_discrepancy"] is True
    assert data["adjusted"] is True

    # Kiểm tra bộ đếm đã được hiệu chỉnh chính xác
    db_session.expire_all()
    counter_after = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "MOTORBIKE",
            )
        )
        .scalars()
        .one()
    )
    assert counter_after.occupied >= 2

    # Kiểm tra counter_events: truy vết được lý do và người làm
    event = (
        db_session.execute(
            select(CounterEvent)
            .where(
                CounterEvent.vehicle_type == "MOTORBIKE",
                CounterEvent.reason == "PERIODIC_AUDIT_NIGHTLY",
            )
            .order_by(CounterEvent.occurred_at.desc())
        )
        .scalars()
        .first()
    )
    assert event is not None
    assert event.reason == "PERIODIC_AUDIT_NIGHTLY"
    assert event.actor_id is not None
    assert "Đối chiếu bộ đếm" in (event.note or "")

    # Kiểm tra audit_logs: ghi nhận hành động RECONCILE_COUNTER
    audit = (
        db_session.execute(
            select(AuditLog)
            .where(
                AuditLog.action == "RECONCILE_COUNTER",
                AuditLog.entity_type == "ParkingCounter",
            )
            .order_by(AuditLog.created_at.desc())
        )
        .scalars()
        .first()
    )
    assert audit is not None
    assert audit.user_id == event.actor_id


def test_compensate_offline_session_increases_counter_and_records_event(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Phiên bù khi mạng lỗi: tăng bộ đếm qua counter_events có lý do và audit."""
    counter_before = (
        db_session.execute(
            select(ParkingCounter).where(
                ParkingCounter.building_id == in_lane.building_id,
                ParkingCounter.vehicle_type == "BICYCLE",
            )
        )
        .scalars()
        .one_or_none()
    )
    initial_occupied = counter_before.occupied if counter_before else 0

    dummy_session_id = str(uuid4())
    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {
        "vehicle_type": "BICYCLE",
        "session_id": dummy_session_id,
        "reason": "NETWORK_OFFLINE_COMPENSATION",
        "note": "Bù phiên xe đạp qua cổng lúc mất mạng cổng 1",
    }
    response = client.post("/api/v1/parking/counters/compensate", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vehicle_type"] == "BICYCLE"
    assert data["occupied"] == initial_occupied + 1
    assert data["delta"] == 1
    assert data["reason"] == "NETWORK_OFFLINE_COMPENSATION"

    # Kiểm tra counter_events
    event = (
        db_session.execute(
            select(CounterEvent)
            .where(
                CounterEvent.vehicle_type == "BICYCLE",
                CounterEvent.reason == "NETWORK_OFFLINE_COMPENSATION",
            )
            .order_by(CounterEvent.occurred_at.desc())
        )
        .scalars()
        .first()
    )
    assert event is not None
    assert event.delta == 1
    assert event.note == "Bù phiên xe đạp qua cổng lúc mất mạng cổng 1"

    # Kiểm tra audit_logs
    audit = (
        db_session.execute(
            select(AuditLog)
            .where(
                AuditLog.action == "COMPENSATE_SESSION",
                AuditLog.entity_type == "ParkingCounter",
            )
            .order_by(AuditLog.created_at.desc())
        )
        .scalars()
        .first()
    )
    assert audit is not None
    assert audit.user_id == event.actor_id


def test_reconcile_when_no_discrepancy(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Khi bộ đếm đã khớp với số phiên PARKED thực tế thì không sinh điều chỉnh thừa."""
    # Đồng bộ bộ đếm cho tất cả các loại xe
    types = ["CAR", "MOTORBIKE", "BICYCLE"]
    for vtype in types:
        count = (
            db_session.execute(
                select(ParkingTransaction).where(
                    ParkingTransaction.building_id == in_lane.building_id,
                    ParkingTransaction.vehicle_type == vtype,
                    ParkingTransaction.status == TransactionStatus.PARKED,
                )
            )
            .scalars()
            .all()
        )
        counter = (
            db_session.execute(
                select(ParkingCounter).where(
                    ParkingCounter.building_id == in_lane.building_id,
                    ParkingCounter.vehicle_type == vtype,
                )
            )
            .scalars()
            .one_or_none()
        )
        if not counter:
            counter = ParkingCounter(
                building_id=in_lane.building_id,
                vehicle_type=vtype,
                occupied=len(count),
            )
            db_session.add(counter)
        else:
            counter.occupied = len(count)
    db_session.commit()

    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {"auto_correct": True, "reason": "REGULAR_AUDIT"}
    response = client.post("/api/v1/parking/counters/reconcile", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["has_discrepancy"] is False
    assert data["adjusted"] is False
    assert len(data["discrepancies"]) == 0
