"""End-to-End Cash Workflow Integration Tests.

Covers:
  - Scenario 1: Casual vehicle IN & OUT with complete cash payment (BR-13, BR-14, BR-23).
  - Scenario 2: Grace period (<= free_minutes) -> fee = 0 VND, auto completes.
  - Scenario 3: Lost ticket penalty -> fee calculated with penalty, completes cleanly.
  - Scenario 4: Subscription vehicle -> valid monthly pass -> fee = 0 VND.
  - Scenario 5: Idempotency & anti-double-charge -> replay with same Idempotency-Key.
  - Scenario 6: Two-step cash payment flow: checkout -> PAYMENT_PENDING -> payment -> COMPLETED.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.buildings.models import DEFAULT_BUILDING_ID
from app.modules.checkin.counter_models import CounterEvent
from app.modules.checkin.lifecycle_models import LifecycleEvent, LifecycleEventType
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.pricing.domain import TicketKind
from app.modules.pricing.models import (
    CustomerClass,
    Invoice,
    Payment,
    PricingRule,
    PricingVersion,
    Subscription,
    TicketProduct,
    Vehicle,
)
from app.modules.users.models import User


@pytest.fixture
def active_lanes(db_session: Session) -> tuple[Lane, Lane]:
    """Ensure active IN and OUT lanes are available for the default building."""
    in_lane = db_session.scalar(
        select(Lane).where(
            Lane.building_id == DEFAULT_BUILDING_ID,
            Lane.direction == LaneDirection.IN,
            Lane.is_active.is_(True),
        )
    )
    out_lane = db_session.scalar(
        select(Lane).where(
            Lane.building_id == DEFAULT_BUILDING_ID,
            Lane.direction == LaneDirection.OUT,
            Lane.is_active.is_(True),
        )
    )
    if in_lane is None:
        in_lane = Lane(
            building_id=DEFAULT_BUILDING_ID,
            name="LANE_IN_CASH_01",
            direction=LaneDirection.IN,
            video_source="test",
            is_active=True,
        )
        db_session.add(in_lane)
    if out_lane is None:
        out_lane = Lane(
            building_id=DEFAULT_BUILDING_ID,
            name="LANE_OUT_CASH_01",
            direction=LaneDirection.OUT,
            video_source="test",
            is_active=True,
        )
        db_session.add(out_lane)
    db_session.commit()
    return in_lane, out_lane


@pytest.fixture
def pricing_setup(db_session: Session) -> dict[str, Any]:
    """
    Set up active pricing configuration for DEFAULT_BUILDING_ID.

    Pricing details:
      - free_minutes: 15
      - initial_minutes: 60, initial_fee: 10,000 VND
      - block_minutes: 60, block_fee: 5,000 VND
      - lost_ticket_fee: 50,000 VND
    """
    admin_user = db_session.scalar(select(User).where(User.username == "admin"))
    admin_id = admin_user.id if admin_user else uuid4()

    customer_class = CustomerClass(
        building_id=DEFAULT_BUILDING_ID,
        code="STANDARD",
        name="Khách vãng lai tiêu chuẩn",
        discount_percent=0,
        active=True,
    )
    db_session.add(customer_class)
    db_session.flush()

    pricing_version = PricingVersion(
        building_id=DEFAULT_BUILDING_ID,
        version_number=1,
        active_from=datetime.now(UTC) - timedelta(days=1),
        created_by_id=admin_id,
    )
    db_session.add(pricing_version)
    db_session.flush()

    car_hourly_rule = PricingRule(
        version_id=pricing_version.id,
        vehicle_type="CAR",
        ticket_kind=TicketKind.HOURLY.value,
        customer_class_id=customer_class.id,
        rule_data={
            "free_minutes": 15,
            "initial_minutes": 60,
            "initial_fee": 10000,
            "block_minutes": 60,
            "block_fee": 5000,
            "lost_ticket_fee": 50000,
            "daily_cap": None,
            "overnight_fee": 0,
            "overtime_fee": 0,
            "day_pass_fee": 0,
            "month_pass_fee": 0,
            "discount_percent": 0,
        },
    )
    car_monthly_rule = PricingRule(
        version_id=pricing_version.id,
        vehicle_type="CAR",
        ticket_kind=TicketKind.MONTHLY.value,
        customer_class_id=customer_class.id,
        rule_data={
            "free_minutes": 15,
            "initial_minutes": 60,
            "initial_fee": 10000,
            "block_minutes": 60,
            "block_fee": 5000,
            "lost_ticket_fee": 50000,
            "month_pass_fee": 1500000,
            "discount_percent": 0,
        },
    )
    db_session.add_all([car_hourly_rule, car_monthly_rule])
    db_session.commit()

    return {
        "customer_class": customer_class,
        "pricing_version": pricing_version,
        "car_hourly_rule": car_hourly_rule,
        "car_monthly_rule": car_monthly_rule,
    }


def test_e2e_cash_workflow_casual_vehicle_in_and_out(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản 1: Xe vãng lai vào và ra thu tiền mặt hoàn chỉnh.

    Flow:
      1. Check-in xe vãng lai (29A12345, CAR, customer_class_id) -> PARKED, bộ đếm +1.
      2. Giả lập đỗ 1h30 (90 phút).
      3. Gọi POST /check-out/preview -> verify duration_minutes, fee_breakdown, tổng 15.000đ.
      4. Gọi POST /check-out với payment_method='CASH' -> COMPLETED, barrier_opened=True.
      5. Xác minh DB: phiên COMPLETED, exit_lane_id cập nhật, bộ đếm giảm (-1 CounterEvent).
    """
    in_lane, out_lane = active_lanes
    plate = "29A12345"
    cust_class = pricing_setup["customer_class"]

    # 1. Check-in xe vãng lai
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201, checkin_res.text
    checkin_data = checkin_res.json()
    tx_data = checkin_data["transaction"]
    assert tx_data["status"] == "PARKED"
    assert tx_data["license_plate"] == plate
    tx_id = UUID(tx_data["id"])

    # Kiểm tra bộ đếm đã tăng khi check-in (BR-14)
    db_session.expire_all()
    checkin_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_IN",
            )
        ).all()
    )
    assert len(checkin_events) == 1
    assert checkin_events[0].delta == 1

    # 2. Giả lập thời gian đỗ 1h30m (90 phút)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=90)
    db_session.commit()

    # 3. Preview tính phí trước khi ra
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        headers=operator_headers,
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
        },
    )
    assert preview_res.status_code == 200, preview_res.text
    pdata = preview_res.json()
    assert pdata["status"] == "PARKED"
    assert pdata["duration_minutes"] >= 90

    # Tính phí chi tiết:
    # 90 phút - 15 phút miễn phí = 75 phút tính tiền.
    # 60 phút đầu (initial) = 10.000 VNĐ.
    # 15 phút tiếp theo (1 block 60p) = 5.000 VNĐ.
    # Tổng cộng = 15.000 VNĐ.
    expected_fee = 15000.0
    assert pdata["fee"] == expected_fee
    assert pdata["fee_breakdown"] is not None
    assert pdata["fee_breakdown"]["total"] == expected_fee
    assert pdata["fee_breakdown"]["duration_minutes"] >= 90
    assert any(
        line.get("code") == "PARKING_DAY" and line.get("amount") == 15000
        for line in pdata["fee_lines"]
    )

    # 4. Check-out thu tiền mặt trực tiếp tại cổng ra
    checkout_key = f"chk-out-cash-{uuid4()}"
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": checkout_key},
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
    )
    assert checkout_res.status_code == 200, checkout_res.text
    cdata = checkout_res.json()
    assert cdata["status"] == "COMPLETED"
    assert cdata["barrier_opened"] is True
    assert cdata["fee"] == expected_fee
    assert cdata["transaction"]["status"] == "COMPLETED"

    # 5. Xác minh dữ liệu trong database
    db_session.expire_all()
    tx_after = db_session.get(ParkingTransaction, tx_id)
    assert tx_after.status == TransactionStatus.COMPLETED
    assert tx_after.exit_lane_id == out_lane.id
    assert tx_after.exit_time is not None
    assert float(tx_after.fee) == expected_fee

    # Kiểm tra sự kiện giảm bộ đếm nguyên tử khi checkout (BR-14)
    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1

    # Verify the persisted billing ledger, not only the HTTP checkout response.
    invoices = list(db_session.scalars(select(Invoice).where(Invoice.transaction_id == tx_id)))
    assert len(invoices) == 1
    assert invoices[0].total_vnd == expected_fee
    payments = list(db_session.scalars(select(Payment).where(Payment.invoice_id == invoices[0].id)))
    assert len(payments) == 1
    assert payments[0].method == "CASH"
    assert payments[0].status == "PAID"
    assert payments[0].amount_vnd == expected_fee
    assert (
        sum(
            event.delta
            for event in db_session.scalars(
                select(CounterEvent).where(CounterEvent.session_id == tx_id)
            )
        )
        == 0
    )

    # Dashboard must reflect the completed session, not count it as parked.
    dashboard_response = client.get(
        "/api/v1/m5/dashboard",
        headers=operator_headers,
        params={"building_id": str(DEFAULT_BUILDING_ID)},
    )
    assert dashboard_response.status_code == 200, dashboard_response.text
    assert dashboard_response.json()["parked"] == 0

    # Kiểm tra sự kiện vòng đời (LifecycleEvent)
    lifecycle_events = list(
        db_session.scalars(
            select(LifecycleEvent)
            .where(LifecycleEvent.session_id == tx_id)
            .order_by(LifecycleEvent.occurred_at.asc())
        ).all()
    )
    event_types = [e.event_type for e in lifecycle_events]
    assert LifecycleEventType.PAYMENT_RECEIVED in event_types
    assert LifecycleEventType.EXIT_CONFIRMED in event_types
    assert LifecycleEventType.BARRIER_OPENED_OUT in event_types
    assert LifecycleEventType.COMPLETED in event_types


def test_e2e_cash_workflow_grace_period(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản 2: Thời gian miễn phí (Grace period).

    Check-in xe và check-out trong vòng 10 phút (< free_minutes=15) -> Phí = 0 VNĐ, COMPLETED.
    """
    in_lane, out_lane = active_lanes
    plate = "29A67890"
    cust_class = pricing_setup["customer_class"]

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # 2. Giả lập xe đỗ 10 phút (dưới mức miễn phí 15 phút)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=10)
    db_session.commit()

    # 3. Preview: Phí phải bằng 0 VNĐ
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        headers=operator_headers,
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
        },
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    assert pdata["duration_minutes"] >= 10
    assert pdata["fee"] == 0.0
    assert pdata["fee_breakdown"]["total"] == 0.0

    # 4. Check-out: Phí = 0đ, không cần thanh toán, tự động mở barrier và COMPLETED
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "payment_method": "CASH",
        },
    )
    assert checkout_res.status_code == 200
    cdata = checkout_res.json()
    assert cdata["status"] == "COMPLETED"
    assert cdata["barrier_opened"] is True
    assert cdata["fee"] == 0.0

    # 5. Xác minh bộ đếm đã giảm
    db_session.expire_all()
    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1


def test_e2e_cash_workflow_lost_ticket_penalty(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản 3: Xử lý xe mất vé (Lost ticket penalty).

    Check-out với cờ is_lost_ticket=True:
      - Tính phí gửi xe thông thường + phụ thu mất vé (50.000 VNĐ).
      - Đóng phiên COMPLETED thành công khi thanh toán tiền mặt.
    """
    in_lane, out_lane = active_lanes
    plate = "29A98765"
    cust_class = pricing_setup["customer_class"]

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # 2. Giả lập đỗ 45 phút
    # (45 - 15 phút free = 30 phút tính tiền -> 1 block 60p đầu = 10.000 VNĐ)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=45)
    db_session.commit()

    # 3. Preview với is_lost_ticket=True
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        headers=operator_headers,
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "is_lost_ticket": True,
        },
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    # 10.000 (phí đỗ) + 50.000 (phạt mất vé) = 60.000 VNĐ
    expected_fee = 60000.0
    assert pdata["fee"] == expected_fee
    assert any(
        line.get("code") == "LOST_TICKET" and line.get("amount") == 50000
        for line in pdata["fee_lines"]
    )

    # 4. Check-out thu tiền mặt với cờ is_lost_ticket=True
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "is_lost_ticket": True,
            "payment_method": "CASH",
        },
    )
    assert checkout_res.status_code == 200
    cdata = checkout_res.json()
    assert cdata["status"] == "COMPLETED"
    assert cdata["barrier_opened"] is True
    assert cdata["fee"] == expected_fee

    # 5. Xác minh DB
    db_session.expire_all()
    tx_after = db_session.get(ParkingTransaction, tx_id)
    assert tx_after.status == TransactionStatus.COMPLETED
    assert float(tx_after.fee) == expected_fee

    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1


def test_e2e_cash_workflow_subscription_vehicle(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản 4: Xe vé tháng (Subscription).

    Tạo xe và gói subscription hợp lệ -> Check-in và Check-out -> Phí = 0 VNĐ.
    """
    in_lane, out_lane = active_lanes
    plate = "29B12345"
    cust_class = pricing_setup["customer_class"]

    # 1. Đăng ký xe và gói vé tháng còn hiệu lực
    vehicle = Vehicle(
        building_id=DEFAULT_BUILDING_ID,
        normalized_plate="29B12345",
        vehicle_type="CAR",
        customer_class_id=cust_class.id,
    )
    db_session.add(vehicle)
    db_session.flush()

    product = TicketProduct(
        building_id=DEFAULT_BUILDING_ID,
        code="MONTHLY_CAR_E2E",
        name="Vé tháng ô tô E2E Test",
        kind=TicketKind.MONTHLY.value,
        vehicle_type="CAR",
        customer_class_id=cust_class.id,
    )
    db_session.add(product)
    db_session.flush()

    sub = Subscription(
        building_id=DEFAULT_BUILDING_ID,
        product_id=product.id,
        vehicle_id=vehicle.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=10),
        valid_until=datetime.now(UTC) + timedelta(days=20),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    # 2. Check-in xe vé tháng
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "MONTHLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # 3. Giả lập xe đỗ 3 giờ (180 phút)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=180)
    db_session.commit()

    # 4. Preview: Phí phải bằng 0 VNĐ
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        headers=operator_headers,
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
        },
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["fee"] == 0.0

    # 5. Check-out: Tự động mở barrier, phí = 0đ, trạng thái COMPLETED
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
        },
    )
    assert checkout_res.status_code == 200
    cdata = checkout_res.json()
    assert cdata["status"] == "COMPLETED"
    assert cdata["barrier_opened"] is True
    assert cdata["fee"] == 0.0

    # 6. Xác minh DB và giảm bộ đếm
    db_session.expire_all()
    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1


def test_e2e_cash_workflow_idempotency_and_no_double_charge(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản 5: Idempotency và chống thu tiền 2 lần.

    Gọi check-out 2 lần với cùng một Idempotency-Key:
      - Lần 1: Check-out thành công, COMPLETED, thu tiền mặt, bộ đếm giảm 1.
      - Lần 2: Trả lại kết quả đã hoàn tất trước đó, không trừ tiền 2 lần, không giảm bộ đếm 2 lần.
    """
    in_lane, out_lane = active_lanes
    plate = "29A55555"
    cust_class = pricing_setup["customer_class"]
    idempotency_key = f"chk-out-idemp-{uuid4()}"

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Giả lập đỗ 90 phút (15.000 VNĐ)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=90)
    db_session.commit()

    # 2. Lần 1: Gọi Check-out với Idempotency-Key
    checkout_payload = {
        "license_plate": plate,
        "exit_lane_id": str(out_lane.id),
        "payment_method": "CASH",
    }
    res1 = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": idempotency_key},
        json=checkout_payload,
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["status"] == "COMPLETED"
    assert body1["barrier_opened"] is True
    assert body1["fee"] == 15000.0

    # Kiểm tra bộ đếm chỉ có 1 event CHECK_OUT
    db_session.expire_all()
    events_after_1 = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(events_after_1) == 1
    assert events_after_1[0].delta == -1

    # Kiểm tra số LifecycleEvent PAYMENT_RECEIVED = 1
    payments_after_1 = list(
        db_session.scalars(
            select(LifecycleEvent).where(
                LifecycleEvent.session_id == tx_id,
                LifecycleEvent.event_type == LifecycleEventType.PAYMENT_RECEIVED,
            )
        ).all()
    )
    assert len(payments_after_1) == 1

    # 3. Lần 2: Gọi Check-out với CÙNG Idempotency-Key
    res2 = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": idempotency_key},
        json=checkout_payload,
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["status"] == "COMPLETED"
    assert body2["barrier_opened"] is True
    assert body2["fee"] == 15000.0
    assert "idempotent" in body2["message"].lower()

    # 4. Xác minh: KHÔNG giảm bộ đếm lần thứ hai (vẫn đúng 1 CounterEvent CHECK_OUT)
    db_session.expire_all()
    events_after_2 = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(events_after_2) == 1

    invoices = list(db_session.scalars(select(Invoice).where(Invoice.transaction_id == tx_id)))
    assert len(invoices) == 1
    payments = list(db_session.scalars(select(Payment).where(Payment.invoice_id == invoices[0].id)))
    assert len(payments) == 1
    assert payments[0].status == "PAID"

    # KHÔNG ghi nhận thanh toán lần thứ 2
    payments_after_2 = list(
        db_session.scalars(
            select(LifecycleEvent).where(
                LifecycleEvent.session_id == tx_id,
                LifecycleEvent.event_type == LifecycleEventType.PAYMENT_RECEIVED,
            )
        ).all()
    )
    assert len(payments_after_2) == 1


def test_e2e_cash_workflow_two_step_payment_flow(
    client, db_session, operator_headers, active_lanes, pricing_setup
):
    """
    Kịch bản mở rộng: Quy trình thu tiền mặt 2 bước:
      Check-out chờ thanh toán -> Thu tiền -> Hoàn tất phiên.

    Flow:
      1. Check-in xe vãng lai.
      2. Check-out không kèm payment_method khi fee > 0 -> PAYMENT_PENDING, barrier CHƯA mở.
      3. Thu tiền mặt qua POST /parking/sessions/{session_id}/payments:
         -> Phiên COMPLETED, barrier mở, bộ đếm giảm.
    """
    in_lane, out_lane = active_lanes
    plate = "29A88888"
    cust_class = pricing_setup["customer_class"]

    # 1. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(cust_class.id),
        },
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Giả lập đỗ 90 phút (15.000 VNĐ)
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=90)
    db_session.commit()

    # 2. Check-out mà chưa chọn payment_method -> Chuyển sang PAYMENT_PENDING, barrier CHƯA mở
    pending_res = client.post(
        "/api/v1/parking/check-out",
        headers={**operator_headers, "Idempotency-Key": f"chk-out-step1-{uuid4()}"},
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
        },
    )
    assert pending_res.status_code == 200
    pdata = pending_res.json()
    assert pdata["status"] == "PAYMENT_PENDING"
    assert pdata["barrier_opened"] is False
    assert pdata["fee"] == 15000.0

    # 3. Thu tiền mặt tại quầy / bốt bảo vệ
    pay_res = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        headers=operator_headers,
        json={
            "payment_method": "CASH",
            "amount": 15000.0,
        },
    )
    assert pay_res.status_code == 200
    cdata = pay_res.json()
    assert cdata["status"] == "COMPLETED"
    assert cdata["barrier_opened"] is True
    assert cdata["fee"] == 15000.0

    # 4. Xác minh bộ đếm đã giảm sau khi hoàn tất thanh toán
    db_session.expire_all()
    checkout_events = list(
        db_session.scalars(
            select(CounterEvent).where(
                CounterEvent.session_id == tx_id,
                CounterEvent.reason == "CHECK_OUT",
            )
        ).all()
    )
    assert len(checkout_events) == 1
    assert checkout_events[0].delta == -1
