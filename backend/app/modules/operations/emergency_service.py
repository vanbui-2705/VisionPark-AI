from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.modules.audit_logs.service import log_action
from app.modules.barriers.models import (
    BarrierAction,
    BarrierStatus,
    BarrierTriggerReason,
)
from app.modules.barriers.service import record_barrier_event
from app.modules.checkin.counter_service import CounterService
from app.modules.checkin.lifecycle_models import ActorType, LifecycleEventType
from app.modules.checkin.lifecycle_service import record_lifecycle_event
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .emergency_schemas import EmergencyExitRequest, EmergencyExitResponse

ACTIVE_SESSION_STATUSES = {
    TransactionStatus.PARKED,
    TransactionStatus.ENTERED,
    TransactionStatus.PAYMENT_PENDING,
    TransactionStatus.PAID,
}


class EmergencyService:
    def __init__(self, db: Session):
        self.db = db

    def open_emergency_exit(
        self,
        lane_id: UUID,
        request: EmergencyExitRequest,
        operator: User,
    ) -> EmergencyExitResponse:
        """
        Kích hoạt chế độ khẩn cấp (PCCC / Sơ tán - dòng 476 nghiepvu.md, BR-23).

        - Mở barrier ngay lập tức với lý do EMERGENCY.
        - Không thu phí (fee = 0.0), không kiểm tra thanh toán.
        - Kết thúc phiên xe đang ở làn ra (nếu có), đánh cờ override và đối soát sau sự cố.
        - Ghi nhận đầy đủ lifecycle_events (BARRIER_OPENED_OUT, COMPLETED).
        - Giảm bộ đếm xe đỗ nguyên tử (CounterService.decrement_atomic).
        """
        # Kiểm tra thẩm quyền thao tác: Accountant không được phép vận hành thiết bị
        if operator.role.name == RoleName.ACCOUNTANT:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Accountant is not authorized to operate emergency exit lanes.",
            )

        lane = self.db.get(Lane, lane_id)
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

        # 1. Khớp phiên gửi xe đang ở làn ra (nếu có thông tin)
        tx: ParkingTransaction | None = None
        if request.session_id:
            tx = self.db.get(ParkingTransaction, request.session_id)
        elif request.license_plate:
            norm = normalize_plate(request.license_plate)
            stmt = select(ParkingTransaction).where(
                ParkingTransaction.normalized_plate == norm,
                ParkingTransaction.status.in_(ACTIVE_SESSION_STATUSES),
            )
            if lane.building_id:
                stmt = stmt.where(ParkingTransaction.building_id == lane.building_id)
            tx = self.db.execute(stmt).scalars().first()
        elif request.ticket_code:
            stmt = select(ParkingTransaction).where(
                ParkingTransaction.ticket_code == request.ticket_code,
                ParkingTransaction.status.in_(ACTIVE_SESSION_STATUSES),
            )
            if lane.building_id:
                stmt = stmt.where(ParkingTransaction.building_id == lane.building_id)
            tx = self.db.execute(stmt).scalars().first()

        # 2. Xử lý kết thúc phiên xe miễn phí và ghi nhận vòng đời
        session_id_val = None
        plate_val = request.license_plate
        session_status = "OPENED"

        if tx and tx.status in ACTIVE_SESSION_STATUSES:
            session_id_val = tx.id
            plate_val = tx.license_plate
            session_status = "COMPLETED"

            tx.status = TransactionStatus.COMPLETED
            tx.exit_lane_id = lane.id
            tx.exit_time = datetime.now(UTC)
            tx.fee = 0.0
            tx.is_manual_override = True

            evac_note = f"[EMERGENCY_EVACUATION: {request.reason}]"
            tx.notes = f"{tx.notes} | {evac_note}" if tx.notes else evac_note

            # Ghi nhận sự kiện vòng đời xe: BARRIER_OPENED_OUT
            record_lifecycle_event(
                session=self.db,
                session_id=tx.id,
                event_type=LifecycleEventType.BARRIER_OPENED_OUT,
                actor_type=ActorType.OPERATOR,
                actor_id=operator.id,
                lane_id=lane.id,
                building_id=lane.building_id or tx.building_id,
                details={
                    "barrier_id": lane.barrier_id,
                    "trigger_reason": BarrierTriggerReason.EMERGENCY,
                    "reason": request.reason,
                    "emergency": True,
                },
            )

            # Ghi nhận sự kiện vòng đời xe: COMPLETED
            record_lifecycle_event(
                session=self.db,
                session_id=tx.id,
                event_type=LifecycleEventType.COMPLETED,
                actor_type=ActorType.OPERATOR,
                actor_id=operator.id,
                lane_id=lane.id,
                building_id=lane.building_id or tx.building_id,
                details={
                    "emergency": True,
                    "reason": request.reason,
                    "fee": 0.0,
                    "fee_waived": True,
                    "requires_post_incident_audit": True,
                    "note": request.note,
                },
            )

            # Giảm bộ đếm xe đỗ nguyên tử
            CounterService.decrement_atomic(
                db=self.db,
                building_id=tx.building_id,
                vehicle_type=tx.vehicle_type,
                session_id=tx.id,
                actor_type="OPERATOR",
                actor_id=operator.id,
                reason="EMERGENCY_EVACUATION",
                note=f"PCCC emergency exit: {request.reason}",
            )

        # 3. Kích hoạt mở barrier và ghi nhận BarrierEvent
        record_barrier_event(
            db=self.db,
            lane_id=lane.id,
            action=BarrierAction.OPEN,
            trigger_reason=BarrierTriggerReason.EMERGENCY,
            status=BarrierStatus.OPEN,
            operator_id=operator.id,
            session_id=session_id_val,
            building_id=lane.building_id,
            barrier_id=lane.barrier_id,
            details={
                "reason": request.reason,
                "emergency": True,
                "note": request.note,
                "source": "EMERGENCY_EXIT_API",
            },
        )

        # 4. Ghi Audit log
        log_action(
            db=self.db,
            user_id=operator.id,
            action="EMERGENCY_BARRIER_OPEN",
            entity_type="Lane",
            entity_id=str(lane.id),
            new_value={
                "reason": request.reason,
                "session_id": str(session_id_val) if session_id_val else None,
                "license_plate": plate_val,
                "emergency": True,
                "note": request.note,
            },
        )

        self.db.commit()

        return EmergencyExitResponse(
            lane_id=lane.id,
            barrier_status=BarrierStatus.OPEN,
            trigger_reason=BarrierTriggerReason.EMERGENCY,
            session_id=session_id_val,
            license_plate=plate_val,
            status=session_status,
            fee=0.0,
            requires_post_incident_audit=True,
            message=(
                "Làn ra đã mở khẩn cấp (PCCC). Phiên xe được xử lý miễn phí "
                "và đánh cờ đối soát sau sự cố."
            ),
        )
