from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.checkin.counter_models import CounterEvent
from app.modules.checkin.lifecycle_models import LifecycleEvent, LifecycleEventType
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane, LaneDirection


def get_lane_by_direction(db_session, direction: LaneDirection):
    return db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )


def test_checkout_preview(client, db_session, operator_headers):
    """Test preview tính phí không làm thay đổi trạng thái phiên."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "30A-999.88"

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201

    # 2. Preview
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    data = preview_res.json()
    assert data["license_plate"] == "30A99988"
    assert data["status"] == "PARKED"
    assert data["duration_minutes"] >= 0
    assert "fee" in data

    # 3. Phiên trong DB vẫn phải là PARKED
    tx = db_session.scalar(
        select(ParkingTransaction).where(ParkingTransaction.normalized_plate == "30A99988")
    )
    assert tx.status == TransactionStatus.PARKED


def test_checkout_success_with_direct_payment(client, db_session, operator_headers):
    """Test xe ra hoàn tất: mở barrier, EXITED -> COMPLETED, giảm bộ đếm (BR-14)."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "29A-111.22"

    # Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    # Check-out
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert checkout_res.status_code == 200
    body = checkout_res.json()
    assert body["status"] == "COMPLETED"
    assert body["barrier_opened"] is True
    assert body["transaction"]["status"] == "COMPLETED"

    # Kiểm tra DB
    db_session.expire_all()
    tx = db_session.get(ParkingTransaction, UUID(tx_id))
    assert tx.status == TransactionStatus.COMPLETED
    assert tx.exit_time is not None
    assert tx.exit_lane_id == out_lane.id

    # Kiểm tra sự kiện giảm bộ đếm nguyên tử (BR-14)
    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == UUID(tx_id),
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1

    # Kiểm tra các sự kiện vòng đời
    events = list(
        db_session.scalars(
            select(LifecycleEvent)
            .where(LifecycleEvent.session_id == tx.id)
            .order_by(LifecycleEvent.occurred_at.asc())
        ).all()
    )
    event_types = [e.event_type for e in events]
    assert LifecycleEventType.EXIT_CONFIRMED in event_types
    assert LifecycleEventType.BARRIER_OPENED_OUT in event_types
    assert LifecycleEventType.COMPLETED in event_types


def test_checkout_bicycle_by_ticket_code(client, db_session, operator_headers):
    """Test xe đạp check-out bằng ticket_code (BR-20)."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    ticket_code = "BIKE-CODE-99"

    # Check-in xe đạp
    client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": str(in_lane.id),
            "vehicle_type": "BICYCLE",
            "ticket_code": ticket_code,
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )

    # Check-out bằng ticket_code
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "ticket_code": ticket_code,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert checkout_res.status_code == 200
    assert checkout_res.json()["status"] == "COMPLETED"
    assert checkout_res.json()["transaction"]["ticket_code"] == ticket_code


def test_checkout_idempotency_reduces_counter_only_once(client, db_session, operator_headers):
    """Test gọi check-out 2 lần cùng Idempotency-Key chỉ giảm bộ đếm đúng 1 lần."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "51H-777.88"
    checkout_key = f"idemp-checkout-{uuid4()}"

    # Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    tx_id = checkin_res.json()["transaction"]["id"]

    # Lần 1: Check-out
    res1 = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": checkout_key},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "COMPLETED"

    db_session.expire_all()
    events1 = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == UUID(tx_id),
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(events1) == 1
    assert events1[0].delta == -1

    # Lần 2: Check-out với CÙNG Idempotency-Key
    res2 = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": checkout_key},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "COMPLETED"
    assert "idempotent" in res2.json()["message"].lower()

    # Bộ đếm KHÔNG được giảm lần thứ hai (chỉ có duy nhất 1 CounterEvent CHECK_OUT)!
    db_session.expire_all()
    events2 = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == UUID(tx_id),
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(events2) == 1


def test_checkout_mismatched_vehicle_type_requires_override(client, db_session, operator_headers):
    """Cảnh báo lệch loại xe (vào CAR, ra MOTORBIKE) nếu không có override."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "43A-666.55"

    client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate, "vehicle_type": "CAR"},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )

    # 1. Không có override_reason -> Bị từ chối 409
    failed_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "vehicle_type_out": "MOTORBIKE",
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert failed_res.status_code == 409
    assert failed_res.json()["code"] == "VEHICLE_TYPE_MISMATCH"

    # 2. Có override_reason -> Chấp nhận cho ra
    success_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "vehicle_type_out": "MOTORBIKE",
            "override_reason": "Bảo vệ xác nhận biển số khớp, camera đọc nhầm loại xe",
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert success_res.status_code == 200
    assert success_res.json()["status"] == "COMPLETED"


def test_checkout_payment_pending_flow(client, db_session, operator_headers):
    """Test luồng thanh toán: phí > 0 -> PAYMENT_PENDING -> thu tiền -> PAID -> COMPLETED."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "60A-333.44"

    # Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    tx_id = checkin_res.json()["transaction"]["id"]

    # Giả lập xe đỗ 3 tiếng trước
    db_session.expire_all()
    db_tx = db_session.get(ParkingTransaction, UUID(tx_id))
    db_tx.check_in_time = datetime.now(UTC) - timedelta(hours=3)
    db_session.commit()

    # Bước 1: Check-out nhưng CHƯA thanh toán (không truyền payment_method)
    step1_res = client.post(
        "/api/v1/parking/check-out",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert step1_res.status_code == 200
    assert step1_res.json()["status"] == "PAYMENT_PENDING"
    assert step1_res.json()["barrier_opened"] is False
    assert step1_res.json()["fee"] > 0

    # Bước 2: Thu tiền qua POST /sessions/{id}/payments
    fee = step1_res.json()["fee"]
    payment_res = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={"payment_method": "CASH", "amount": fee},
        headers=operator_headers,
    )
    assert payment_res.status_code == 200
    assert payment_res.json()["status"] == "COMPLETED"
    assert payment_res.json()["barrier_opened"] is True


def test_checkout_lost_ticket_adds_fee(client, db_session, operator_headers):
    """Test mất vé/thẻ áp phí mất vé theo quy định."""
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "72A-555.99"

    client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )

    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "is_lost_ticket": True,
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert checkout_res.status_code == 200
    assert checkout_res.json()["fee"] >= 50000.0
    assert checkout_res.json()["status"] == "COMPLETED"
