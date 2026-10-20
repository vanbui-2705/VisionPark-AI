from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.barriers.models import (
    BarrierAction,
    BarrierEvent,
    BarrierStatus,
    BarrierTriggerReason,
)
from app.modules.buildings.models import DEFAULT_BUILDING_ID, UserBuilding
from app.modules.checkin.counter_models import ParkingCounter
from app.modules.checkin.counter_service import CounterService
from app.modules.checkin.lifecycle_models import LifecycleEvent, LifecycleEventType
from app.modules.checkin.models import (
    CheckInSource,
    ParkingTransaction,
    TransactionStatus,
    VehicleType,
)
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName
from tests.conftest import login


def get_lane(db_session, direction: LaneDirection) -> Lane:
    return db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )


def role_headers(client, db_session, role_name: RoleName) -> dict[str, str]:
    role = db_session.scalar(select(Role).where(Role.name == role_name.value))
    username = f"user_{role_name.value.lower()}_{uuid4().hex[:6]}"
    user = User(
        username=username,
        display_name=username,
        password_hash=hash_password("role-test-password"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserBuilding(user_id=user.id, building_id=DEFAULT_BUILDING_ID))
    db_session.commit()
    token = login(client, username, "role-test-password")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_parked_session(
    db_session,
    lane_id: UUID,
    plate: str = "29A-999.99",
    vtype: str = VehicleType.CAR,
) -> ParkingTransaction:
    now = datetime.now(UTC)
    tx = ParkingTransaction(
        id=uuid4(),
        building_id=DEFAULT_BUILDING_ID,
        license_plate=plate,
        normalized_plate=plate.replace("-", "").replace(".", "").replace(" ", "").upper(),
        ticket_code=f"TKT-{uuid4().hex[:8].upper()}",
        vehicle_type=vtype,
        status=TransactionStatus.PARKED,
        lane_id=lane_id,
        check_in_time=now,
        source=CheckInSource.AI_ACCEPTED,
        fee=25000.0,
        idempotency_key=str(uuid4()),
        request_fingerprint="f" * 64,
    )
    db_session.add(tx)

    # Đảm bảo bộ đếm đã tăng
    counter = CounterService.get_or_create_counter(db_session, DEFAULT_BUILDING_ID, vtype)
    counter.occupied = max(1, counter.occupied + 1)
    db_session.commit()
    return tx


def test_get_availability_endpoint(client):
    """GET /api/v1/availability trả danh sách chỗ trống cho màn hình cổng (BR-04, BR-13)."""
    res = client.get("/api/v1/availability")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    types = {item["vehicle_type"] for item in data}
    assert {"CAR", "MOTORBIKE", "BICYCLE"}.issubset(types)

    for item in data:
        assert "occupied" in item
        assert "safe_capacity" in item
        assert "available" in item
        assert "status" in item
        assert item["status"] in {"AVAILABLE", "NEARLY_FULL", "FULL"}


def test_emergency_open_with_active_session(client, db_session, operator_headers):
    """
    Mở làn ra khẩn cấp (PCCC):
    - Barrier mở ngay lập tức với lý do EMERGENCY.
    - Miễn phí vé (fee=0.0), không kiểm tra luồng tiền.
    - Chuyển trạng thái COMPLETED, đánh cờ override và đối soát sau sự cố.
    - Trừ bộ đếm và ghi nhận lifecycle_events (BR-08, BR-23, dòng 476 nghiepvu.md).
    """
    exit_lane = get_lane(db_session, LaneDirection.OUT)
    in_lane = get_lane(db_session, LaneDirection.IN)

    # Tạo phiên đang đỗ
    tx = create_parked_session(db_session, in_lane.id, plate="30E-123.45", vtype=VehicleType.CAR)
    initial_occupied = db_session.scalar(
        select(ParkingCounter.occupied).where(
            ParkingCounter.building_id == DEFAULT_BUILDING_ID,
            ParkingCounter.vehicle_type == VehicleType.CAR,
        )
    )

    res = client.post(
        f"/api/v1/emergency/lanes/{exit_lane.id}/open",
        json={
            "session_id": str(tx.id),
            "reason": "HOA_HOAN_TANG_HAM_B2",
            "note": "Báo cháy từ hệ thống PCCC tòa nhà",
        },
        headers=operator_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["barrier_status"] == BarrierStatus.OPEN
    assert data["trigger_reason"] == BarrierTriggerReason.EMERGENCY
    assert data["session_id"] == str(tx.id)
    assert data["status"] == "COMPLETED"
    assert data["fee"] == 0.0
    assert data["requires_post_incident_audit"] is True

    # 1. Kiểm tra trạng thái phiên trong DB
    db_session.expire_all()
    updated_tx = db_session.get(ParkingTransaction, tx.id)
    assert updated_tx.status == TransactionStatus.COMPLETED
    assert updated_tx.fee == 0.0
    assert updated_tx.is_manual_override is True
    assert updated_tx.exit_lane_id == exit_lane.id
    assert updated_tx.exit_time is not None
    assert "HOA_HOAN_TANG_HAM_B2" in updated_tx.notes

    # 2. Kiểm tra bộ đếm đã giảm
    new_occupied = db_session.scalar(
        select(ParkingCounter.occupied).where(
            ParkingCounter.building_id == DEFAULT_BUILDING_ID,
            ParkingCounter.vehicle_type == VehicleType.CAR,
        )
    )
    assert new_occupied == initial_occupied - 1

    # 3. Kiểm tra BarrierEvent
    barrier_event = db_session.scalar(
        select(BarrierEvent).where(
            BarrierEvent.lane_id == exit_lane.id,
            BarrierEvent.trigger_reason == BarrierTriggerReason.EMERGENCY,
        )
    )
    assert barrier_event is not None
    assert barrier_event.action == BarrierAction.OPEN
    assert barrier_event.status == BarrierStatus.OPEN

    # 4. Kiểm tra LifecycleEvent
    events = (
        db_session.execute(
            select(LifecycleEvent)
            .where(LifecycleEvent.session_id == tx.id)
            .order_by(LifecycleEvent.occurred_at.asc())
        )
        .scalars()
        .all()
    )
    event_types = [e.event_type for e in events]
    assert LifecycleEventType.BARRIER_OPENED_OUT in event_types
    assert LifecycleEventType.COMPLETED in event_types

    completed_event = next(e for e in events if e.event_type == LifecycleEventType.COMPLETED)
    assert completed_event.details["emergency"] is True
    assert completed_event.details["fee_waived"] is True
    assert completed_event.details["requires_post_incident_audit"] is True


def test_emergency_open_lane_without_session(client, db_session, operator_headers):
    """Mở làn ra xả trạm sơ tán (không chỉ định xe cụ thể)."""
    exit_lane = get_lane(db_session, LaneDirection.OUT)

    res = client.post(
        f"/api/v1/emergency/lanes/{exit_lane.id}/open",
        json={
            "reason": "SO_TAN_TOAN_BO",
            "note": "Xả toàn bộ cổng ra khẩn cấp",
        },
        headers=operator_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["barrier_status"] == BarrierStatus.OPEN
    assert data["trigger_reason"] == BarrierTriggerReason.EMERGENCY
    assert data["session_id"] is None
    assert data["status"] == "OPENED"


def test_emergency_checkout_alias_by_plate(client, db_session, operator_headers):
    """Endpoint POST /api/v1/checkout/emergency khớp xe theo biển số xe thoát ra."""
    exit_lane = get_lane(db_session, LaneDirection.OUT)
    in_lane = get_lane(db_session, LaneDirection.IN)

    tx = create_parked_session(db_session, in_lane.id, plate="51H-888.88", vtype=VehicleType.CAR)

    res = client.post(
        "/api/v1/checkout/emergency",
        json={
            "lane_id": str(exit_lane.id),
            "license_plate": "51H-888.88",
            "reason": "PCCC_COI_BAO_CHAY",
        },
        headers=operator_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["session_id"] == str(tx.id)
    assert data["status"] == "COMPLETED"
    assert data["fee"] == 0.0

    db_session.expire_all()
    updated_tx = db_session.get(ParkingTransaction, tx.id)
    assert updated_tx.status == TransactionStatus.COMPLETED
    assert updated_tx.fee == 0.0


def test_emergency_open_unauthorized_role_blocked(client, db_session):
    """Vai trò kế toán (ACCOUNTANT) không có quyền kích hoạt chế độ khẩn cấp làn (403)."""
    exit_lane = get_lane(db_session, LaneDirection.OUT)
    accountant_headers = role_headers(client, db_session, RoleName.ACCOUNTANT)

    res = client.post(
        f"/api/v1/emergency/lanes/{exit_lane.id}/open",
        json={"reason": "PCCC"},
        headers=accountant_headers,
    )
    assert res.status_code == 403
