"""
Test suite cho Thành viên 2 (Backend Core & Tariff Integration):
- M2-01: Tối ưu Check-Out Preview (duration_minutes, fee_breakdown, chẵn tiền, ảnh vào, < 100ms)
- M2-02: Check-Out Tiền Mặt 1 Chạm (CASH -> COMPLETED, giảm counter, mở barrier ngay)
- M2-03: Logic Xử lý Mất vé (Lost Ticket -> áp dụng lost_ticket_fee, ghi log audit)
- M2-04: Rà soát API Mở Barrier (trigger PAYMENT_RECEIVED, action OPEN, barrier_opened: True)
"""

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.audit_logs.models import AuditLog
from app.modules.barriers.models import BarrierAction, BarrierEvent, BarrierTriggerReason
from app.modules.checkin.counter_models import CounterEvent
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane, LaneDirection


def get_lane_by_direction(db_session, direction: LaneDirection) -> Lane:
    lane = db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )
    assert lane is not None, f"Làn {direction} không tồn tại trong DB test."
    return lane


def test_m2_01_checkout_preview_details_and_latency(client, db_session, operator_headers):
    """
    M2-01: Kiểm tra POST /parking/check-out/preview
    - Trả về duration_minutes >= 0
    - Trả về công thức tính fee_breakdown (có formula, lines, total, currency)
    - Số tiền chẵn fee
    - Link ảnh lúc vào check_in_image_url
    - Phản hồi nhanh dưới 100ms
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "30E-888.99"

    # 1. Tạo phiên check-in kèm image_url
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Cập nhật ảnh vào và thời gian vào giả lập cách đây 125 phút
    db_tx = db_session.get(ParkingTransaction, tx_id)
    db_tx.image_url = "/api/v1/alpr/media/lane_in_test_snapshot.jpg"
    db_tx.check_in_time = datetime.now(UTC) - timedelta(minutes=125)
    db_session.commit()

    # 2. Gọi POST /parking/check-out/preview và đo thời gian phản hồi
    t_start = time.perf_counter()
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    t_elapsed_ms = (time.perf_counter() - t_start) * 1000

    assert preview_res.status_code == 200
    data = preview_res.json()

    # Kiểm tra các trường nghiệp vụ theo tiêu chuẩn DoD
    assert data["session_id"] == str(tx_id)
    assert data["duration_minutes"] >= 125
    assert isinstance(data["fee"], (int, float))
    assert data["fee"] == round(data["fee"])  # Số tiền chẵn
    assert data["check_in_image_url"] == "/api/v1/alpr/media/lane_in_test_snapshot.jpg"

    # Kiểm tra cấu trúc fee_breakdown
    breakdown = data["fee_breakdown"]
    assert breakdown is not None
    assert "formula" in breakdown
    assert "duration_minutes" in breakdown
    assert "lines" in breakdown
    assert breakdown["total"] == data["fee"]

    # DoD: Latency < 100ms
    assert t_elapsed_ms < 100.0, f"Preview latency {t_elapsed_ms:.2f}ms vượt quá 100ms"


def test_m2_02_cash_checkout_one_touch_completed(client, db_session, operator_headers):
    """
    M2-02: Đóng phiên Check-Out Tiền Mặt 1 Chạm
    - Gửi payload { exit_lane_id, payment_method: "CASH" }
    - Tự động đóng phiên COMPLETED trong 1 request duy nhất (không có trạng thái chờ)
    - Giảm bộ đếm chỗ đỗ
    - Mở barrier ngay lập tức
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "29C-333.22"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Đóng phiên với CASH
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
    res_data = checkout_res.json()

    # Phải COMPLETED ngay, không được là PAYMENT_PENDING
    assert res_data["status"] == "COMPLETED"
    assert res_data["barrier_opened"] is True
    assert res_data["transaction"]["status"] == "COMPLETED"

    # Kiểm tra DB
    db_session.expire_all()
    tx = db_session.get(ParkingTransaction, tx_id)
    assert tx.status == TransactionStatus.COMPLETED
    assert tx.exit_time is not None
    assert tx.exit_lane_id == out_lane.id

    # Kiểm tra giảm bộ đếm 1 lần duy nhất
    events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(events) == 1
    assert events[0].delta == -1


def test_m2_03_lost_ticket_logic_and_audit(client, db_session, operator_headers):
    """
    M2-03: Logic Xử lý Mất vé (Lost Ticket)
    - is_lost_ticket = True -> Áp dụng lost_ticket_fee của bãi xe
    - Ghi log audit kiểm toán (action LOST_TICKET_PROCESSED)
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "51G-999.11"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Gán snapshot cấu hình lost_ticket_fee = 50.000đ
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.price_snapshot = {
        "version_id": str(uuid4()),
        "rule_id": str(uuid4()),
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class": "STANDARD",
        "free_minutes": 15,
        "initial_minutes": 60,
        "initial_fee": 5000,
        "block_minutes": 60,
        "block_fee": 5000,
        "lost_ticket_fee": 50000,
    }
    db_session.commit()

    # 1. Preview với is_lost_ticket = True
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id), "is_lost_ticket": True},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert any(line["code"] == "LOST_TICKET" for line in p_data["fee_lines"])
    assert p_data["fee"] >= 50000.0

    # 2. Checkout báo mất vé và thanh toán CASH
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
    c_data = checkout_res.json()
    assert c_data["status"] == "COMPLETED"
    assert c_data["fee"] >= 50000.0

    # 3. Kiểm tra log kiểm toán (AuditLog) trong database
    db_session.expire_all()
    audit_logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_id == str(tx_id),
                AuditLog.action.in_(["LOST_TICKET_PROCESSED", "LOST_TICKET_PREVIEW"]),
            )
        ).all()
    )
    assert len(audit_logs) >= 1
    processed_log = next((log for log in audit_logs if log.action == "LOST_TICKET_PROCESSED"), None)
    assert processed_log is not None
    assert processed_log.new_value.get("is_lost_ticket") is True
    assert processed_log.new_value.get("lost_ticket_fee") == 50000.0


def test_m2_04_barrier_event_trigger_payment_received(client, db_session, operator_headers):
    """
    M2-04: Rà soát API Mở Barrier
    - Khi xe thanh toán tiền mặt thành công -> backend gọi record_barrier_event
    - action: OPEN
    - trigger_reason: PAYMENT_RECEIVED
    - cờ barrier_opened: True ngay lập tức
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "14A-444.88"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Giả lập xe đỗ 2 tiếng để phát sinh phí gửi xe
    db_session.expire_all()
    db_tx = db_session.get(ParkingTransaction, tx_id)
    db_tx.check_in_time = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    # Check-out thanh toán CASH
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
    res_data = checkout_res.json()
    assert res_data["barrier_opened"] is True
    assert res_data["status"] == "COMPLETED"

    # Kiểm tra bản ghi BarrierEvent tại làn ra (exit lane) trong DB
    db_session.expire_all()
    out_barrier_event = db_session.scalar(
        select(BarrierEvent)
        .where(
            BarrierEvent.session_id == tx_id,
            BarrierEvent.lane_id == out_lane.id,
            BarrierEvent.action == BarrierAction.OPEN,
        )
        .order_by(BarrierEvent.created_at.desc())
    )
    assert out_barrier_event is not None
    assert out_barrier_event.action == "OPEN"
    assert out_barrier_event.trigger_reason == BarrierTriggerReason.PAYMENT_RECEIVED
    assert out_barrier_event.status == "OPEN"
