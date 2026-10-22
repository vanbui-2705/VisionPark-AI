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
from app.modules.checkin.lifecycle_models import LifecycleEvent
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
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


def test_open_barrier_normal_success(client, db_session, operator_headers):
    """Mở barrier thông thường (NORMAL) thành công, ghi nhận BarrierEvent (BR-08, BR-23)."""
    lane = get_lane(db_session, LaneDirection.IN)

    res = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "NORMAL"},
        headers=operator_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["action"] == BarrierAction.OPEN
    assert data["status"] == BarrierStatus.OPEN
    assert data["trigger_reason"] == BarrierTriggerReason.NORMAL
    assert data["lane_id"] == str(lane.id)
    assert data["timeout_seconds"] == 15

    # Kiểm tra DB
    event = db_session.scalar(select(BarrierEvent).where(BarrierEvent.id == UUID(data["id"])))
    assert event is not None
    assert event.trigger_reason == "NORMAL"
    assert event.status == "OPEN"


def test_open_barrier_override_success(client, db_session, operator_headers):
    """Mở barrier override thành công khi có quyền và lý do (BR-08, BR-23)."""
    lane = get_lane(db_session, LaneDirection.OUT)

    res = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={
            "trigger_reason": "OVERRIDE",
            "override_reason": "Xe ưu tiên cứu thương",
            "timeout_seconds": 30,
        },
        headers=operator_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["action"] == BarrierAction.OPEN
    assert data["trigger_reason"] == BarrierTriggerReason.OVERRIDE
    assert data["timeout_seconds"] == 30
    assert data["details"]["override_reason"] == "Xe ưu tiên cứu thương"


def test_open_barrier_override_missing_reason_rejected(client, db_session, operator_headers):
    """Mở override không có lý do bị từ chối với lỗi 422 (BR-23)."""
    lane = get_lane(db_session, LaneDirection.IN)

    res = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "OVERRIDE", "override_reason": ""},
        headers=operator_headers,
    )
    assert res.status_code == 422
    assert res.json()["code"] == "OVERRIDE_REASON_REQUIRED"


def test_open_barrier_unauthorized_role_blocked(client, db_session):
    """Vai trò không có quyền vận hành barrier (ACCOUNTANT) bị chặn 403 (BR-08)."""
    lane = get_lane(db_session, LaneDirection.IN)
    headers = role_headers(client, db_session, RoleName.ACCOUNTANT)

    res = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "NORMAL"},
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    res_override = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "OVERRIDE", "override_reason": "Thử override"},
        headers=headers,
    )
    assert res_override.status_code == 403
    assert res_override.json()["code"] == "FORBIDDEN"


def test_open_barrier_emergency_mode(client, db_session, operator_headers):
    """Mở barrier chế độ khẩn cấp (EMERGENCY) ghi lý do và người thao tác (BR-23)."""
    lane = get_lane(db_session, LaneDirection.OUT)

    res = client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "EMERGENCY"},
        headers=operator_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["trigger_reason"] == BarrierTriggerReason.EMERGENCY
    assert data["status"] == BarrierStatus.OPEN


def test_close_barrier_vehicle_passed(client, db_session, operator_headers):
    """Đóng barrier khi xe đã đi qua (VEHICLE_PASSED)."""
    lane = get_lane(db_session, LaneDirection.IN)

    res = client.post(
        f"/api/v1/gates/{lane.id}/close",
        json={"reason": "VEHICLE_PASSED"},
        headers=operator_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == BarrierAction.CLOSE
    assert data["status"] == BarrierStatus.CLOSED
    assert data["trigger_reason"] == "VEHICLE_PASSED"


def test_barrier_timeout_auto_close_preserves_session_status(client, db_session, operator_headers):
    """
    Xe không qua sau thời gian chờ: đóng barrier, giữ nguyên trạng thái phiên, báo cảnh báo.
    (Mục 3.4 & 4.7 trong nghiepvu.md).
    """
    in_lane = get_lane(db_session, LaneDirection.IN)
    plate = "29A-888.99"

    # 1. Tạo phiên check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"to-chk-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    # 2. Giả lập mở barrier cho phiên này
    open_res = client.post(
        f"/api/v1/gates/{in_lane.id}/open",
        json={"trigger_reason": "NORMAL", "session_id": tx_id, "timeout_seconds": 15},
        headers=operator_headers,
    )
    assert open_res.status_code == 200

    # 3. Hết thời gian chờ xe không qua -> trigger đóng barrier do timeout
    close_res = client.post(
        f"/api/v1/gates/{in_lane.id}/close",
        json={"reason": "TIMEOUT_AUTO_CLOSE", "session_id": tx_id},
        headers=operator_headers,
    )
    assert close_res.status_code == 200
    close_data = close_res.json()
    assert close_data["action"] == BarrierAction.CLOSE
    assert close_data["status"] == BarrierStatus.CLOSED_TIMEOUT
    assert close_data["trigger_reason"] == BarrierTriggerReason.TIMEOUT_AUTO_CLOSE
    assert "warning" in close_data["details"]

    # 4. Trạng thái phiên gửi xe PHẢI GIỮ NGUYÊN (PARKED, không bị nhảy sang EXITED/COMPLETED)
    tx = db_session.scalar(select(ParkingTransaction).where(ParkingTransaction.id == UUID(tx_id)))
    assert tx.status == TransactionStatus.PARKED

    # 5. Có ghi nhận sự kiện vòng đời cảnh báo timeout
    lc_events = db_session.scalars(
        select(LifecycleEvent).where(LifecycleEvent.session_id == UUID(tx_id))
    ).all()
    event_types = [e.event_type for e in lc_events]
    assert "BARRIER_TIMEOUT_CLOSED" in event_types


def test_list_barrier_events_audit(client, db_session, operator_headers):
    """Truy vấn danh sách sự kiện barrier có lọc theo làn và lý do (BR-23)."""
    lane = get_lane(db_session, LaneDirection.IN)

    # Tạo vài sự kiện
    client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "NORMAL"},
        headers=operator_headers,
    )
    client.post(
        f"/api/v1/gates/{lane.id}/open",
        json={"trigger_reason": "OVERRIDE", "override_reason": "Audit test override"},
        headers=operator_headers,
    )

    res = client.get(
        f"/api/v1/barriers/events?lane_id={lane.id}&trigger_reason=OVERRIDE",
        headers=operator_headers,
    )
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    for ev in events:
        assert ev["lane_id"] == str(lane.id)
        assert ev["trigger_reason"] == "OVERRIDE"


def test_barrier_events_recorded_during_checkin_and_checkout(client, db_session, operator_headers):
    """Check-in và Check-out tự động ghi nhận BarrierEvent trong cùng transaction (BR-08, BR-23)."""
    in_lane = get_lane(db_session, LaneDirection.IN)
    out_lane = get_lane(db_session, LaneDirection.OUT)
    plate = "51H-999.01"

    # Check-in
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-barrier-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    # BarrierEvent tại cổng vào
    in_event = db_session.scalar(
        select(BarrierEvent).where(
            BarrierEvent.session_id == UUID(tx_id),
            BarrierEvent.lane_id == in_lane.id,
        )
    )
    assert in_event is not None
    assert in_event.action == BarrierAction.OPEN
    assert in_event.status == BarrierStatus.OPEN

    # Check-out
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={"license_plate": plate, "exit_lane_id": str(out_lane.id)},
        headers={**operator_headers, "Idempotency-Key": f"chko-barrier-{uuid4()}"},
    )
    assert checkout_res.status_code == 200

    # BarrierEvent tại cổng ra
    out_event = db_session.scalar(
        select(BarrierEvent).where(
            BarrierEvent.session_id == UUID(tx_id),
            BarrierEvent.lane_id == out_lane.id,
        )
    )
    assert out_event is not None
    assert out_event.action == BarrierAction.OPEN
    assert out_event.status == BarrierStatus.OPEN
