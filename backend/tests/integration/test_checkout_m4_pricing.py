from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.buildings.models import DEFAULT_BUILDING_ID
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.checkin.service import normalize_plate
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.pricing.domain import TicketKind
from app.modules.pricing.models import (
    CustomerClass,
    PricingRule,
    PricingVersion,
    Subscription,
    TicketProduct,
    Vehicle,
)


def get_lane_by_direction(db_session, direction: LaneDirection):
    return db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )


def test_price_snapshot_isolation_when_pricing_changes(client, db_session, operator_headers):
    """
    BR-13: Đổi bảng giá giữa chừng không làm đổi phí của xe đang trong bãi.
    Snapshot giá lúc vào được giữ nguyên độc lập với cấu hình giá mới.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "30A-888.99"
    fixed_version_id = uuid4()

    # 1. Xe check-in với snapshot giá 10.000đ/giờ
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Giả lập gán price_snapshot và lùi check_in_time về 65 phút trước
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=65)
    tx.price_snapshot = {
        "version_id": str(fixed_version_id),
        "rule_id": str(uuid4()),
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class": "STANDARD",
        "free_minutes": 15,
        "initial_minutes": 60,
        "initial_fee": 10000,
        "block_minutes": 60,
        "block_fee": 10000,
        "lost_ticket_fee": 50000,
    }
    db_session.commit()

    # 2. Tạo một phiên bản giá mới toanh trên hệ thống tăng giá gấp 10 lần (100.000đ)
    admin_user_id = db_session.scalar(select(ParkingTransaction.id)) or uuid4()
    cust_class = CustomerClass(
        building_id=DEFAULT_BUILDING_ID,
        code="VIP_HIGH",
        name="VIP",
        discount_percent=0,
    )
    db_session.add(cust_class)
    db_session.flush()

    new_version = PricingVersion(
        building_id=DEFAULT_BUILDING_ID,
        version_number=99,
        active_from=datetime.now(UTC) - timedelta(hours=1),
        created_by_id=admin_user_id,
    )
    db_session.add(new_version)
    db_session.flush()

    new_rule = PricingRule(
        version_id=new_version.id,
        vehicle_type="CAR",
        ticket_kind="HOURLY",
        customer_class_id=cust_class.id,
        rule_data={
            "initial_fee": 100000,
            "block_fee": 100000,
        },
    )
    db_session.add(new_rule)
    db_session.commit()

    # 3. Xe check-out preview: phí vẫn phải tính theo snapshot (10.000đ initial fee)
    # chứ KHÔNG phải theo phiên bản giá mới (100.000đ)
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    assert pdata["fee"] == 10000.0
    assert pdata["fee_breakdown"]["price_version_id"] == str(fixed_version_id)
    assert len(pdata["fee_lines"]) > 0


def test_checkout_valid_monthly_subscription(client, db_session, operator_headers):
    """
    BR-07, BR-14: Vé tháng còn hạn, biển số khớp -> Phí = 0đ, mở barrier đi thẳng.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "29B-555.55"
    norm_plate = normalize_plate(plate)

    # 1. Tạo bản ghi xe và vé tháng còn hạn
    vehicle = Vehicle(
        building_id=DEFAULT_BUILDING_ID,
        normalized_plate=norm_plate,
        vehicle_type="CAR",
    )
    db_session.add(vehicle)
    db_session.flush()

    product = TicketProduct(
        building_id=DEFAULT_BUILDING_ID,
        code="MONTHLY_CAR_TEST",
        name="Vé tháng ô tô test",
        kind=TicketKind.MONTHLY.value,
        vehicle_type="CAR",
    )
    db_session.add(product)
    db_session.flush()

    sub = Subscription(
        building_id=DEFAULT_BUILDING_ID,
        product_id=product.id,
        vehicle_id=vehicle.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=15),
        valid_until=datetime.now(UTC) + timedelta(days=15),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    # 2. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201

    # 3. Preview: Phí phải bằng 0đ
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["fee"] == 0.0

    # 4. Check-out: Không cần truyền payment_method, tự động mở barrier và COMPLETED
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers={**operator_headers, "Idempotency-Key": f"chk-out-{uuid4()}"},
    )
    assert checkout_res.status_code == 200
    cdata = checkout_res.json()
    assert cdata["fee"] == 0.0
    assert cdata["barrier_opened"] is True
    assert cdata["status"] == TransactionStatus.COMPLETED


def test_checkout_expired_monthly_subscription_beyond_grace(client, db_session, operator_headers):
    """
    BR-07: Vé tháng hết hạn quá ân hạn -> Tính như vé lượt theo snapshot cho lần ra này.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "29B-777.77"
    norm_plate = normalize_plate(plate)

    # 1. Tạo bản ghi xe và vé tháng đã hết hạn 10 ngày trước (grace_days = 3)
    vehicle = Vehicle(
        building_id=DEFAULT_BUILDING_ID,
        normalized_plate=norm_plate,
        vehicle_type="CAR",
    )
    db_session.add(vehicle)
    db_session.flush()

    product = TicketProduct(
        building_id=DEFAULT_BUILDING_ID,
        code="MONTHLY_EXP_TEST",
        name="Vé tháng hết hạn test",
        kind=TicketKind.MONTHLY.value,
        vehicle_type="CAR",
    )
    db_session.add(product)
    db_session.flush()

    sub = Subscription(
        building_id=DEFAULT_BUILDING_ID,
        product_id=product.id,
        vehicle_id=vehicle.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=40),
        valid_until=datetime.now(UTC) - timedelta(days=10),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    # 2. Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Giả lập thời gian gửi xe 90 phút trước, snapshot giá lượt 15.000đ/giờ
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=90)
    tx.price_snapshot = {
        "version_id": str(uuid4()),
        "rule_id": str(uuid4()),
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class": "STANDARD",
        "free_minutes": 0,
        "initial_minutes": 60,
        "initial_fee": 15000,
        "block_minutes": 60,
        "block_fee": 15000,
        "lost_ticket_fee": 50000,
    }
    db_session.commit()

    # 3. Preview: Phí phải tính theo vé lượt: 15.000 + 15.000 = 30.000đ
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["fee"] == 30000.0


def test_checkout_lost_ticket_fee(client, db_session, operator_headers):
    """
    BR-13: Mất vé/mất thẻ -> Tính giá vé lượt cộng phụ thu lost_ticket_fee từ snapshot.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "51F-123.45"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = UUID(checkin_res.json()["transaction"]["id"])

    # Gán snapshot với lost_ticket_fee = 70.000đ và initial_fee = 10.000đ
    tx = db_session.get(ParkingTransaction, tx_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=30)
    tx.price_snapshot = {
        "version_id": str(uuid4()),
        "rule_id": str(uuid4()),
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class": "STANDARD",
        "free_minutes": 0,
        "initial_minutes": 60,
        "initial_fee": 10000,
        "block_minutes": 60,
        "block_fee": 10000,
        "lost_ticket_fee": 70000,
    }
    db_session.commit()

    # 1. Preview thông thường (không mất vé) -> 10.000đ
    preview_normal = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_normal.status_code == 200
    assert preview_normal.json()["fee"] == 10000.0

    # 2. Preview báo mất vé (is_lost_ticket = True) -> 10.000đ + 70.000đ = 80.000đ
    preview_lost = client.post(
        "/api/v1/parking/check-out/preview",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id), "is_lost_ticket": True},
        headers=operator_headers,
    )
    assert preview_lost.status_code == 200
    assert preview_lost.json()["fee"] == 80000.0
    # Phải có fee line cho LOST_TICKET
    lines = preview_lost.json()["fee_lines"]
    assert any(line.get("code") == "LOST_TICKET" for line in lines)


def test_checkout_bicycle_pricing(client, db_session, operator_headers):
    """
    Acceptance Criteria: Xe đạp quét mã vé, tính theo bảng giá xe đạp từ snapshot.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    ticket_code = "BIKE-2026-001"

    import hashlib

    # Tạo phiên xe đạp có ticket_code
    tx = ParkingTransaction(
        building_id=DEFAULT_BUILDING_ID,
        lane_id=in_lane.id,
        ticket_code=ticket_code,
        license_plate=None,
        normalized_plate=None,
        vehicle_type="BICYCLE",
        source="MANUAL_ENTRY",
        idempotency_key=f"chk-in-bike-{uuid4()}",
        request_fingerprint=hashlib.sha256(f"bike-{uuid4()}".encode()).hexdigest(),
        check_in_time=datetime.now(UTC) - timedelta(minutes=45),
        status=TransactionStatus.PARKED,
        price_snapshot={
            "version_id": str(uuid4()),
            "rule_id": str(uuid4()),
            "vehicle_type": "BICYCLE",
            "ticket_kind": "HOURLY",
            "customer_class": "STANDARD",
            "free_minutes": 0,
            "initial_minutes": 120,
            "initial_fee": 3000,
            "block_minutes": 60,
            "block_fee": 2000,
            "lost_ticket_fee": 20000,
        },
    )
    db_session.add(tx)
    db_session.commit()

    # Check-out preview bằng ticket_code
    preview_res = client.post(
        "/api/v1/parking/check-out/preview",
        json={"ticket_code": ticket_code, "exit_lane_id": str(out_lane.id)},
        headers=operator_headers,
    )
    assert preview_res.status_code == 200
    data = preview_res.json()
    assert data["ticket_code"] == ticket_code
    assert data["vehicle_type_in"] == "BICYCLE"
    assert data["fee"] == 3000.0
