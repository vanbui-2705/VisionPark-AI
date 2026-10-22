from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit_logs.service import log_action
from app.modules.checkin.lifecycle_models import ActorType, LifecycleEventType
from app.modules.checkin.lifecycle_service import record_lifecycle_event
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.users.models import User
from app.modules.users.permissions import has_permission
from app.modules.users.schemas import RoleName

from .models import BarrierAction, BarrierEvent, BarrierStatus, BarrierTriggerReason
from .schemas import BarrierCloseRequest, BarrierOpenRequest

VALID_OPEN_REASONS = {
    BarrierTriggerReason.NORMAL,
    BarrierTriggerReason.OVERRIDE,
    BarrierTriggerReason.EMERGENCY,
}


def record_barrier_event(
    db: Session,
    lane_id: UUID,
    action: str,
    trigger_reason: str,
    status: str,
    operator_id: UUID | None = None,
    session_id: UUID | None = None,
    building_id: UUID | None = None,
    barrier_id: str | None = None,
    timeout_seconds: int = 15,
    details: dict | None = None,
) -> BarrierEvent:
    """Ghi nhận sự kiện barrier vào DB trong cùng một transaction (BR-08, BR-23)."""
    event = BarrierEvent(
        building_id=building_id,
        lane_id=lane_id,
        barrier_id=barrier_id,
        action=action,
        trigger_reason=trigger_reason,
        operator_id=operator_id,
        session_id=session_id,
        status=status,
        timeout_seconds=timeout_seconds,
        details=details,
    )
    db.add(event)
    db.flush()

    if operator_id and trigger_reason == BarrierTriggerReason.OVERRIDE:
        log_action(
            db=db,
            user_id=operator_id,
            action="BARRIER_OVERRIDE",
            entity_type="BarrierEvent",
            entity_id=str(event.id),
            new_value={
                "lane_id": str(lane_id),
                "action": action,
                "trigger_reason": trigger_reason,
                "status": status,
                "barrier_id": barrier_id,
                "session_id": str(session_id) if session_id else None,
            },
        )
    return event


class BarrierService:
    def __init__(self, session: Session):
        self.session = session

    def open_barrier(
        self,
        lane_id: UUID,
        request: BarrierOpenRequest,
        operator: User,
    ) -> BarrierEvent:
        """
        Mở barrier mô phỏng theo quyền (BR-08) và ghi lý do kích hoạt (BR-23).

        - NORMAL: Mở tự động qua Access Control hoặc luồng check-in/check-out.
        - OVERRIDE: Yêu cầu quyền override_barrier và bắt buộc có override_reason.
        - EMERGENCY: Chế độ khẩn cấp (PCCC/sơ tán), yêu cầu quyền thích hợp.
        - Chặn hoàn toàn vai trò không có quyền vận hành (ACCOUNTANT).
        """
        lane = self.session.get(Lane, lane_id)
        if not lane:
            raise AppError(
                status_code=404,
                code="LANE_NOT_FOUND",
                message=f"Lane {lane_id} not found.",
            )

        if not lane.is_active:
            raise AppError(
                status_code=400,
                code="LANE_INACTIVE",
                message=f"Lane {lane_id} is inactive.",
            )

        if request.trigger_reason not in VALID_OPEN_REASONS:
            raise AppError(
                status_code=422,
                code="INVALID_TRIGGER_REASON",
                message=(
                    f"Invalid trigger_reason '{request.trigger_reason}'. "
                    "Allowed: NORMAL, OVERRIDE, EMERGENCY."
                ),
            )

        if operator.role.name == RoleName.ACCOUNTANT:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Accountant is not authorized to operate barriers.",
            )

        if request.trigger_reason == BarrierTriggerReason.OVERRIDE:
            if not has_permission(operator, "override_barrier"):
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN",
                    message="Permission 'override_barrier' required to override barrier (BR-08).",
                )
            if not request.override_reason or not request.override_reason.strip():
                raise AppError(
                    status_code=422,
                    code="OVERRIDE_REASON_REQUIRED",
                    message=(
                        "override_reason is required when trigger_reason is OVERRIDE "
                        "(BR-08, BR-23)."
                    ),
                )

        if request.session_id:
            tx = self.session.get(ParkingTransaction, request.session_id)
            if not tx:
                raise AppError(
                    status_code=404,
                    code="SESSION_NOT_FOUND",
                    message=f"Parking transaction {request.session_id} not found.",
                )
            event_type = (
                LifecycleEventType.BARRIER_OPENED_IN
                if lane.direction == LaneDirection.IN
                else LifecycleEventType.BARRIER_OPENED_OUT
            )
            record_lifecycle_event(
                session=self.session,
                session_id=tx.id,
                event_type=event_type,
                actor_type=ActorType.OPERATOR,
                actor_id=operator.id,
                lane_id=lane.id,
                building_id=lane.building_id,
                details={
                    "barrier_id": lane.barrier_id,
                    "trigger_reason": request.trigger_reason,
                    "override_reason": request.override_reason,
                    "timeout_seconds": request.timeout_seconds,
                },
            )

        details = {
            "override_reason": request.override_reason,
            "source": "OPERATOR_OPEN",
        }

        event = record_barrier_event(
            db=self.session,
            lane_id=lane.id,
            building_id=lane.building_id,
            barrier_id=lane.barrier_id,
            action=BarrierAction.OPEN,
            trigger_reason=request.trigger_reason,
            operator_id=operator.id,
            session_id=request.session_id,
            status=BarrierStatus.OPEN,
            timeout_seconds=request.timeout_seconds,
            details=details,
        )
        self.session.commit()
        return event

    def close_barrier(
        self,
        lane_id: UUID,
        request: BarrierCloseRequest,
        operator: User,
    ) -> BarrierEvent:
        """
        Đóng barrier mô phỏng (BR-08, BR-23).

        - VEHICLE_PASSED: Xe đã đi qua cổng thành công.
        - TIMEOUT_AUTO_CLOSE / TIMEOUT_EXPIRED: Xe không qua, hết thời gian chờ
          -> Tự động đóng barrier, giữ nguyên trạng thái phiên, ghi cảnh báo.
        """
        lane = self.session.get(Lane, lane_id)
        if not lane:
            raise AppError(
                status_code=404,
                code="LANE_NOT_FOUND",
                message=f"Lane {lane_id} not found.",
            )

        if operator.role.name == RoleName.ACCOUNTANT:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Accountant is not authorized to operate barriers.",
            )

        is_timeout = request.reason in {
            BarrierTriggerReason.TIMEOUT_AUTO_CLOSE,
            "TIMEOUT_EXPIRED",
            "TIMEOUT",
        }

        if is_timeout:
            status = BarrierStatus.CLOSED_TIMEOUT
            trigger_reason = BarrierTriggerReason.TIMEOUT_AUTO_CLOSE
            details = {
                "warning": "Barrier timed out before vehicle passed. Session status preserved.",
                "reason": request.reason,
            }

            if request.session_id:
                tx = self.session.get(ParkingTransaction, request.session_id)
                if tx:
                    # BR-23 & 4.7: Hết thời gian chờ thì đóng barrier, giữ nguyên trạng thái phiên
                    details["preserved_session_status"] = str(tx.status)
                    record_lifecycle_event(
                        session=self.session,
                        session_id=tx.id,
                        event_type="BARRIER_TIMEOUT_CLOSED",
                        actor_type=ActorType.SYSTEM,
                        actor_id=operator.id,
                        lane_id=lane.id,
                        building_id=lane.building_id,
                        details={
                            "warning": "Vehicle did not pass within timeout. Status preserved.",
                            "preserved_status": str(tx.status),
                        },
                    )
        else:
            status = BarrierStatus.CLOSED
            trigger_reason = request.reason
            details = {"close_reason": request.reason}

            if request.session_id and request.reason == BarrierTriggerReason.VEHICLE_PASSED:
                tx = self.session.get(ParkingTransaction, request.session_id)
                if tx and lane.direction == LaneDirection.OUT:
                    record_lifecycle_event(
                        session=self.session,
                        session_id=tx.id,
                        event_type=LifecycleEventType.EXIT_CONFIRMED,
                        actor_type=ActorType.SYSTEM,
                        actor_id=operator.id,
                        lane_id=lane.id,
                        building_id=lane.building_id,
                        details={"barrier_id": lane.barrier_id},
                    )

        event = record_barrier_event(
            db=self.session,
            lane_id=lane.id,
            building_id=lane.building_id,
            barrier_id=lane.barrier_id,
            action=BarrierAction.CLOSE,
            trigger_reason=trigger_reason,
            operator_id=operator.id,
            session_id=request.session_id,
            status=status,
            details=details,
        )
        self.session.commit()
        return event

    def list_events(
        self,
        lane_id: UUID | None = None,
        building_id: UUID | None = None,
        trigger_reason: str | None = None,
        session_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BarrierEvent]:
        """Truy vấn danh sách sự kiện barrier cho audit và giám sát vận hành."""
        stmt = select(BarrierEvent).order_by(BarrierEvent.created_at.desc())
        if lane_id is not None:
            stmt = stmt.where(BarrierEvent.lane_id == lane_id)
        if building_id is not None:
            stmt = stmt.where(BarrierEvent.building_id == building_id)
        if trigger_reason is not None:
            stmt = stmt.where(BarrierEvent.trigger_reason == trigger_reason)
        if session_id is not None:
            stmt = stmt.where(BarrierEvent.session_id == session_id)

        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())
