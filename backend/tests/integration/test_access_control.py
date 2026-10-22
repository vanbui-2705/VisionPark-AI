from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.checkin.lifecycle_models import LifecycleEvent, LifecycleEventType
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


@pytest.fixture
def motorbike_only_lane(db_session: Session) -> Lane:
    lane = db_session.query(Lane).filter_by(name="LANE_MOTO_ONLY").first()
    if not lane:
        lane = Lane(
            name="LANE_MOTO_ONLY",
            direction=LaneDirection.IN,
            video_source="rtsp://dummy_moto",
            is_active=True,
            allowed_vehicle_type=AllowedVehicleType.MOTORBIKE,
        )
        db_session.add(lane)
        db_session.commit()
    return lane


def test_checkin_success_records_access_decided_event(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Xe hợp lệ check-in sinh sự kiện ACCESS_DECIDED (ALLOW) cùng transaction."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    plate = "30A12399"
    payload = {
        "lane_id": str(in_lane.id),
        "license_plate": plate,
        "vehicle_type": "CAR",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["transaction"]["license_plate"] == plate
    assert data["transaction"]["vehicle_type"] == "CAR"
    assert data["transaction"]["status"] == TransactionStatus.PARKED

    tx_id = data["transaction"]["id"]
    events = (
        db_session.execute(
            select(LifecycleEvent)
            .where(LifecycleEvent.session_id == UUID(tx_id))
            .order_by(LifecycleEvent.occurred_at.asc())
        )
        .scalars()
        .all()
    )
    event_types = [e.event_type for e in events]
    assert LifecycleEventType.ACCESS_DECIDED in event_types
    assert LifecycleEventType.CHECKED_IN in event_types

    access_event = next(e for e in events if e.event_type == LifecycleEventType.ACCESS_DECIDED)
    assert access_event.details["decision"] == "ALLOW"
    assert access_event.details["vehicle_type"] == "CAR"


def test_checkin_denied_when_vehicle_type_not_allowed_on_lane(
    client: TestClient, operator_token: str, motorbike_only_lane: Lane
):
    """Ô tô vào làn chỉ cho phép xe máy bị từ chối ACCESS_DENIED (403)."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload = {
        "lane_id": str(motorbike_only_lane.id),
        "license_plate": "30A99988",
        "vehicle_type": "CAR",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 403, response.text
    err = response.json()
    assert err["code"] == "ACCESS_DENIED"
    assert "does not allow vehicle type 'CAR'" in err["message"]


def test_checkin_denied_when_blacklisted_plate(
    client: TestClient, operator_token: str, in_lane: Lane
):
    """Biển số trong blacklist (stub M1) bị từ chối ACCESS_DENIED (403)."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload = {
        "lane_id": str(in_lane.id),
        "license_plate": "29A-99999",
        "vehicle_type": "CAR",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 403, response.text
    err = response.json()
    assert err["code"] == "ACCESS_DENIED"
    assert "blacklist" in err["message"].lower()


def test_checkin_bicycle_without_plate_succeeds_with_ticket_code(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Xe đạp không có biển số nhưng có ticket_code tạo phiên thành công (BR-20)."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    ticket_code = f"BIKE-{uuid4().hex[:8]}"
    payload = {
        "lane_id": str(in_lane.id),
        "vehicle_type": "BICYCLE",
        "ticket_code": ticket_code,
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["transaction"]["license_plate"] is None
    assert data["transaction"]["vehicle_type"] == "BICYCLE"
    assert data["transaction"]["ticket_code"] == ticket_code

    tx_id = data["transaction"]["id"]
    tx = db_session.get(ParkingTransaction, UUID(tx_id))
    assert tx.license_plate is None
    assert tx.ticket_code == ticket_code


def test_checkin_bicycle_without_ticket_code_rejected(
    client: TestClient, operator_token: str, in_lane: Lane
):
    """Xe đạp không có biển số và không có ticket_code bị từ chối hợp lệ."""
    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload = {
        "lane_id": str(in_lane.id),
        "vehicle_type": "BICYCLE",
    }
    response = client.post("/api/v1/parking/check-in", json=payload, headers=headers)
    assert response.status_code == 422


def test_checkin_bicycle_duplicate_ticket_code_rejected(
    client: TestClient, operator_token: str, in_lane: Lane
):
    """Hai xe đạp dùng trùng ticket_code khi phiên đang mở bị chặn (BR-20)."""
    headers1 = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    ticket_code = f"BIKE-DUP-{uuid4().hex[:6]}"
    payload = {
        "lane_id": str(in_lane.id),
        "vehicle_type": "BICYCLE",
        "ticket_code": ticket_code,
    }
    first = client.post("/api/v1/parking/check-in", json=payload, headers=headers1)
    assert first.status_code == 201, first.text

    headers2 = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    payload2 = {
        "lane_id": str(in_lane.id),
        "vehicle_type": "BICYCLE",
        "ticket_code": ticket_code,
    }
    second = client.post("/api/v1/parking/check-in", json=payload2, headers=headers2)
    assert second.status_code == 409
    assert second.json()["code"] == "TICKET_ALREADY_ACTIVE"


def test_access_check_endpoint(
    client: TestClient,
    operator_token: str,
    in_lane: Lane,
    motorbike_only_lane: Lane,
):
    """Kiểm tra endpoint POST /api/v1/parking/access-check."""
    headers = {"Authorization": f"Bearer {operator_token}"}

    # Case 1: ALLOW
    res1 = client.post(
        "/api/v1/parking/access-check",
        json={"lane_id": str(in_lane.id), "license_plate": "51A11122", "vehicle_type": "CAR"},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res1.json()["decision"] == "ALLOW"

    # Case 2: DENY (sai làn)
    res2 = client.post(
        "/api/v1/parking/access-check",
        json={
            "lane_id": str(motorbike_only_lane.id),
            "license_plate": "51A11122",
            "vehicle_type": "CAR",
        },
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["decision"] == "DENY"

    # Case 3: DENY (blacklist)
    res3 = client.post(
        "/api/v1/parking/access-check",
        json={
            "lane_id": str(in_lane.id),
            "license_plate": "29A-99999",
            "vehicle_type": "CAR",
        },
        headers=headers,
    )
    assert res3.status_code == 200
    assert res3.json()["decision"] == "DENY"


def test_checkin_subscription_valid_allows_entry(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Xe có vé tháng M4 còn hiệu lực được phép vào bãi (ALLOW)."""
    from datetime import UTC, datetime, timedelta

    from app.alpr.utils import normalize_plate
    from app.modules.pricing.models import CustomerClass, Subscription, TicketProduct, Vehicle

    b_id = in_lane.building_id
    c_class = CustomerClass(building_id=b_id, code=f"RES-{uuid4().hex[:6]}", name="Resident")
    db_session.add(c_class)
    db_session.flush()

    prod = TicketProduct(
        building_id=b_id,
        code=f"M-CAR-{uuid4().hex[:6]}",
        name="Ve Thang Oto",
        kind="MONTHLY",
        vehicle_type="CAR",
        customer_class_id=c_class.id,
    )
    db_session.add(prod)
    db_session.flush()

    plate = f"30M{uuid4().hex[:5].upper()}"
    veh = Vehicle(
        building_id=b_id,
        normalized_plate=normalize_plate(plate),
        vehicle_type="CAR",
        customer_class_id=c_class.id,
    )
    db_session.add(veh)
    db_session.flush()

    sub = Subscription(
        building_id=b_id,
        product_id=prod.id,
        vehicle_id=veh.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_until=datetime.now(UTC) + timedelta(days=29),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    response = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate, "vehicle_type": "CAR"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["transaction"]["license_plate"] == plate


def test_checkin_subscription_expired_allowed_as_visitor(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Xe có vé tháng M4 đã hết hạn vẫn được vào bãi theo dạng vé lượt (BR-07, ALLOW 201)."""
    from datetime import UTC, datetime, timedelta

    from app.alpr.utils import normalize_plate
    from app.modules.pricing.models import CustomerClass, Subscription, TicketProduct, Vehicle

    b_id = in_lane.building_id
    c_class = CustomerClass(building_id=b_id, code=f"EXP-{uuid4().hex[:6]}", name="ExpiredClass")
    db_session.add(c_class)
    db_session.flush()

    prod = TicketProduct(
        building_id=b_id,
        code=f"EXP-PROD-{uuid4().hex[:6]}",
        name="Ve Thang Het Han",
        kind="MONTHLY",
        vehicle_type="CAR",
        customer_class_id=c_class.id,
    )
    db_session.add(prod)
    db_session.flush()

    plate = f"30E{uuid4().hex[:5].upper()}"
    veh = Vehicle(
        building_id=b_id,
        normalized_plate=normalize_plate(plate),
        vehicle_type="CAR",
        customer_class_id=c_class.id,
    )
    db_session.add(veh)
    db_session.flush()

    sub = Subscription(
        building_id=b_id,
        product_id=prod.id,
        vehicle_id=veh.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=40),
        valid_until=datetime.now(UTC) - timedelta(days=10),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    response = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate, "vehicle_type": "CAR"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["transaction"]["license_plate"] == plate


def test_checkin_subscription_vehicle_type_mismatch_denied(
    client: TestClient, operator_token: str, in_lane: Lane, db_session: Session
):
    """Xe có vé tháng đăng ký loại xe khác với loại xe thực tế vào làn bị từ chối (DENY 403)."""
    from datetime import UTC, datetime, timedelta

    from app.alpr.utils import normalize_plate
    from app.modules.pricing.models import CustomerClass, Subscription, TicketProduct, Vehicle

    b_id = in_lane.building_id
    c_class = CustomerClass(building_id=b_id, code=f"MIS-{uuid4().hex[:6]}", name="MismatchClass")
    db_session.add(c_class)
    db_session.flush()

    prod = TicketProduct(
        building_id=b_id,
        code=f"MIS-PROD-{uuid4().hex[:6]}",
        name="Ve Thang Xe May",
        kind="MONTHLY",
        vehicle_type="MOTORBIKE",
        customer_class_id=c_class.id,
    )
    db_session.add(prod)
    db_session.flush()

    plate = f"30M{uuid4().hex[:5].upper()}"
    veh = Vehicle(
        building_id=b_id,
        normalized_plate=normalize_plate(plate),
        vehicle_type="MOTORBIKE",
        customer_class_id=c_class.id,
    )
    db_session.add(veh)
    db_session.flush()

    sub = Subscription(
        building_id=b_id,
        product_id=prod.id,
        vehicle_id=veh.id,
        zone_id=uuid4(),
        valid_from=datetime.now(UTC) - timedelta(days=1),
        valid_until=datetime.now(UTC) + timedelta(days=29),
        grace_days=3,
    )
    db_session.add(sub)
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {operator_token}",
        "Idempotency-Key": str(uuid4()),
    }
    # Xe vào làn nhưng khai báo loại xe CAR thay vì MOTORBIKE
    response = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate, "vehicle_type": "CAR"},
        headers=headers,
    )
    assert response.status_code == 403, response.text
    err = response.json()
    assert err["code"] == "ACCESS_DENIED"
