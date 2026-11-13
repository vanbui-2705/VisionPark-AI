"""Integration and E2E tests for M3 Demo Readiness items
(docs/demo-readiness-improvement-plan-2026-11-08.md):
- BUILD-01: Checkout idempotency record & payload fingerprint verification
- BUILD-02 / DEMO-03: Checkout ledger orchestration (Invoice + Payment sync)
- BUILD-07 / DEMO-12: Full E2E flow (check-in -> counter -> preview -> CASH -> ledger
  -> counter -> M5 report -> audit)
- DEMO-01 / IMPROVE-01: Payment method validation
- DEMO-02 / IMPROVE-01: Payment amount validation & admin override check
- IMPROVE-02: Simulated barrier labeling
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.modules.audit_logs.models import AuditLog
from app.modules.buildings.models import DEFAULT_BUILDING_ID, Building
from app.modules.checkin.counter_models import CounterEvent, ParkingCounter
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.pricing.models import Invoice, Payment


def _get_lane(db_session, direction: LaneDirection) -> Lane:
    lane = db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )
    assert lane is not None
    return lane


def test_demo_01_rejects_unknown_payment_method(client, db_session, operator_headers):
    """DEMO-01 / IMPROVE-01: Chuỗi payment_method lạ bị từ chối với mã INVALID_PAYMENT_METHOD."""
    in_lane = _get_lane(db_session, LaneDirection.IN)
    out_lane = _get_lane(db_session, LaneDirection.OUT)
    plate = "29A-701.01"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    # 1. Direct checkout với payment_method lạ -> 422 INVALID_PAYMENT_METHOD
    bad_checkout = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CRYPTO_UNKNOWN",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert bad_checkout.status_code == 422
    assert bad_checkout.json()["code"] == "INVALID_PAYMENT_METHOD"

    # 2. record_payment với payment_method lạ -> 422 INVALID_PAYMENT_METHOD
    bad_pay = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={"payment_method": "BITCOIN", "amount": 5000},
        headers=operator_headers,
    )
    assert bad_pay.status_code == 422
    assert bad_pay.json()["code"] == "INVALID_PAYMENT_METHOD"


def test_demo_02_record_payment_validates_amount_and_override_role(
    client, db_session, operator_headers, admin_token
):
    """DEMO-02 / IMPROVE-01: Kiểm tra thu thiếu, thu thừa và phân quyền override."""
    in_lane = _get_lane(db_session, LaneDirection.IN)
    out_lane = _get_lane(db_session, LaneDirection.OUT)
    plate = "29A-702.02"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Lùi check_in_time 2 giờ để phát sinh phí > 0
    db_tx = db_session.get(ParkingTransaction, tx_id)
    db_tx.check_in_time = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    # Chuyển phiên sang PAYMENT_PENDING
    pending_res = client.post(
        "/api/v1/parking/check-out",
        json={"session_id": str(tx_id), "exit_lane_id": str(out_lane.id)},
        headers={**operator_headers, "Idempotency-Key": f"chk-pending-{uuid4()}"},
    )
    assert pending_res.status_code == 200
    assert pending_res.json()["status"] == "PAYMENT_PENDING"
    due_fee = pending_res.json()["fee"]
    assert due_fee > 0

    # 1. Thu thiếu (underpayment) -> 409 PAYMENT_AMOUNT_MISMATCH, phiên vẫn PAYMENT_PENDING
    under_res = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={"payment_method": "CASH", "amount": due_fee - 1000},
        headers=operator_headers,
    )
    assert under_res.status_code == 409
    assert under_res.json()["code"] == "PAYMENT_AMOUNT_MISMATCH"
    db_session.expire_all()
    assert db_session.get(ParkingTransaction, tx_id).status == TransactionStatus.PAYMENT_PENDING

    # 2. Thu thừa (overpayment) không có override -> 409 PAYMENT_AMOUNT_MISMATCH
    over_res = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={"payment_method": "CASH", "amount": due_fee + 5000},
        headers=operator_headers,
    )
    assert over_res.status_code == 409
    assert over_res.json()["code"] == "PAYMENT_AMOUNT_MISMATCH"

    # 3. Operator thường thử OVERRIDE miễn phí -> 403 OVERRIDE_FORBIDDEN
    op_override = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={
            "payment_method": "OVERRIDE",
            "amount": 0,
            "override_reason": "Khách VIP của tòa nhà",
        },
        headers=operator_headers,
    )
    assert op_override.status_code == 403
    assert op_override.json()["code"] == "OVERRIDE_FORBIDDEN"

    # 4. Admin thực hiện OVERRIDE có lý do -> 200 OK, Invoice WAIVED
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_override = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={
            "payment_method": "OVERRIDE",
            "amount": 0,
            "override_reason": "Ban quản lý duyệt miễn phí sự kiện",
        },
        headers=admin_headers,
    )
    assert admin_override.status_code == 200
    body = admin_override.json()
    assert body["status"] == "COMPLETED"
    assert body["fee"] == 0.0
    assert body["barrier_mode"] == "SIMULATED"
    assert body["barrier_event_recorded"] is True

    db_session.expire_all()
    inv = db_session.scalar(select(Invoice).where(Invoice.transaction_id == tx_id))
    assert inv is not None
    assert inv.status == "WAIVED"


def test_build_01_checkout_idempotency_replay_and_payload_conflict(
    client, db_session, operator_headers
):
    """BUILD-01: Retry cùng key + payload trả kết quả cũ; khác payload trả 409."""
    in_lane = _get_lane(db_session, LaneDirection.IN)
    out_lane = _get_lane(db_session, LaneDirection.OUT)
    plate = "29A-703.03"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    db_tx = db_session.get(ParkingTransaction, tx_id)
    db_tx.check_in_time = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    key = f"checkout-idemp-{uuid4()}"
    payload = {
        "license_plate": plate,
        "exit_lane_id": str(out_lane.id),
        "payment_method": "CASH",
    }

    # 1. Lần gọi đầu tiên -> 200 OK
    first = client.post(
        "/api/v1/parking/check-out",
        json=payload,
        headers={**operator_headers, "Idempotency-Key": key},
    )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["invoice_id"] is not None
    assert first_data["payment_id"] is not None

    # 2. Replay cùng key + cùng payload -> 200 OK, không tạo trùng Invoice/Payment/CounterEvent
    second = client.post(
        "/api/v1/parking/check-out",
        json=payload,
        headers={**operator_headers, "Idempotency-Key": key},
    )
    assert second.status_code == 200
    assert second.json()["invoice_id"] == first_data["invoice_id"]
    assert second.json()["payment_id"] == first_data["payment_id"]

    db_session.expire_all()
    assert (
        db_session.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.transaction_id == tx_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.invoice_id == UUID(first_data["invoice_id"]))
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(CounterEvent)
            .where(CounterEvent.session_id == tx_id, CounterEvent.reason == "CHECK_OUT")
        )
        == 1
    )

    # 3. Replay cùng key nhưng payload khác (is_lost_ticket=True) -> 409 IDEMPOTENCY_KEY_REUSED
    conflict = client.post(
        "/api/v1/parking/check-out",
        json={**payload, "is_lost_ticket": True},
        headers={**operator_headers, "Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_build_02_and_build_07_e2e_cash_checkout_ledger_counter_m5_and_audit(
    client, db_session, operator_headers, admin_token
):
    """
    BUILD-02, BUILD-07, DEMO-03, DEMO-04, DEMO-12:
    Kiểm thử E2E xuyên suốt:
    check-in -> counter tăng -> preview checkout -> CASH payment -> invoice/payment
    -> checkout complete -> counter giảm -> M5 daily-stats & cash-shifts -> audit
    """
    in_lane = _get_lane(db_session, LaneDirection.IN)
    out_lane = _get_lane(db_session, LaneDirection.OUT)
    plate = "30K-888.66"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate, "vehicle_type": "CAR"},
        headers={**operator_headers, "Idempotency-Key": f"e2e-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Kiểm tra counter tăng = 1
    db_session.expire_all()
    occupied_in = db_session.scalar(
        select(ParkingCounter.occupied).where(
            ParkingCounter.building_id == DEFAULT_BUILDING_ID,
            ParkingCounter.vehicle_type == "CAR",
        )
    )
    assert occupied_in == 1

    # Giả lập đỗ 90 phút để có phí > 0
    db_tx = db_session.get(ParkingTransaction, tx_id)
    db_tx.check_in_time = datetime.now(UTC) - timedelta(minutes=90)
    db_session.commit()

    # 2. Preview checkout
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"session_id": str(tx_id), "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    expected_fee = int(preview_res.json()["fee"])
    assert expected_fee > 0

    # 3. Direct CASH checkout
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "session_id": str(tx_id),
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
            "expected_fee": expected_fee,
        },
        headers={**operator_headers, "Idempotency-Key": f"e2e-out-{tx_id}"},
    )
    assert checkout_res.status_code == 200
    out_data = checkout_res.json()
    assert out_data["status"] == "COMPLETED"
    assert out_data["fee"] == expected_fee
    assert out_data["barrier_opened"] is True
    assert out_data["barrier_event_recorded"] is True
    assert out_data["barrier_mode"] == "SIMULATED"
    assert out_data["invoice_id"] is not None
    assert out_data["payment_id"] is not None

    # 4. Kiểm tra counter giảm về 0
    db_session.expire_all()
    occupied_out = db_session.scalar(
        select(ParkingCounter.occupied).where(
            ParkingCounter.building_id == DEFAULT_BUILDING_ID,
            ParkingCounter.vehicle_type == "CAR",
        )
    )
    assert occupied_out == 0

    # 5. Kiểm tra M5 Daily Stats & Cash Shift Report khớp 100% với phí vừa thu
    building = db_session.get(Building, DEFAULT_BUILDING_ID)
    building.timezone = "UTC"
    db_tx = db_session.get(ParkingTransaction, tx_id)
    checkout_utc = (db_tx.exit_time or datetime.now(UTC)).replace(tzinfo=UTC)
    db_tx.check_in_time = checkout_utc
    db_session.commit()

    today_str = checkout_utc.date().isoformat()
    rebuild_res = client.post(
        f"/api/v1/m5/daily-stats/rebuild?building_id={DEFAULT_BUILDING_ID}&day={today_str}",
        headers=admin_headers,
    )
    assert rebuild_res.status_code == 200
    daily = rebuild_res.json()
    assert int(daily["entries"]) == 1
    assert int(daily["exits"]) == 1
    assert int(float(daily["revenue"])) == expected_fee
    assert int(daily["occupancy_peak"]) == 1

    shift_start = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    shift_end = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    shift_res = client.get(
        "/api/v1/m5/cash-shifts",
        params={
            "building_id": str(DEFAULT_BUILDING_ID),
            "start": shift_start,
            "end": shift_end,
        },
        headers=admin_headers,
    )
    assert shift_res.status_code == 200
    shift = shift_res.json()
    assert shift["entries"] == 1
    assert shift["exits"] == 1
    assert shift["cash_revenue_vnd"] == expected_fee

    # 6. Kiểm tra AuditLog ghi nhận cả PAYMENT_RECEIVED và CHECKOUT_COMPLETED
    audit_actions = list(
        db_session.scalars(select(AuditLog.action).where(AuditLog.entity_id == str(tx_id))).all()
    )
    assert "PAYMENT_RECEIVED" in audit_actions
    assert "CHECKOUT_COMPLETED" in audit_actions
