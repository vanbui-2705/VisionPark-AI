from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.database.idempotency import validate_idempotency_key
from app.modules.audit_logs.service import log_action
from app.modules.barriers import (
    BarrierAction,
    BarrierStatus,
    BarrierTriggerReason,
    record_barrier_event,
)
from app.modules.checkin.counter_service import CounterService
from app.modules.checkin.lifecycle_models import ActorType, LifecycleEventType
from app.modules.checkin.lifecycle_service import record_lifecycle_event
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.checkin.repository import CheckInRepository
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.users.models import User

from .schemas import CheckOutPreviewResponse, CheckOutRequest, CheckOutResponse

# Trạng thái phiên được phép checkout (BR-14)
_CHECKOUT_ELIGIBLE = {
    TransactionStatus.PARKED,
    TransactionStatus.PAYMENT_PENDING,
    TransactionStatus.PAID,
}


def _normalize_tz(dt: datetime) -> datetime:
    """Đảm bảo datetime luôn có timezone UTC để tính toán an toàn."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _calculate_fee_stub(
    transaction: ParkingTransaction,
    exit_time: datetime,
    is_lost_ticket: bool = False,
) -> tuple[float, dict]:
    """
    STUB tính phí — tính theo biểu mẫu đơn giản chờ Module M4 hoàn thiện.

    TODO[M4]: Bỏ stub này, nối calculate_fee() từ module pricing của M4 (P3-M3-09).
    """
    price_snapshot = getattr(transaction, "price_snapshot", None) or {}
    free_minutes: int = price_snapshot.get("free_minutes", 0)
    t_in = _normalize_tz(transaction.check_in_time)
    t_out = _normalize_tz(exit_time)
    duration_minutes = max(0, int((t_out - t_in).total_seconds() // 60))

    if duration_minutes <= free_minutes:
        fee = 0.0
    else:
        rate_per_hour: float = price_snapshot.get("rate_per_hour", 5000.0)
        billable_hours = (duration_minutes - free_minutes + 59) // 60
        fee = float(rate_per_hour * billable_hours)

    if is_lost_ticket:
        lost_fee: float = price_snapshot.get("lost_ticket_fee", 50000.0)
        fee += lost_fee

    breakdown = {
        "stub": True,
        "duration_minutes": duration_minutes,
        "free_minutes": free_minutes,
        "base_fee": fee,
        "note": "TODO[M4]: Replace with real Pricing Engine",
    }
    return fee, breakdown


class CheckOutService:
    def __init__(self, repository: CheckInRepository, session: Session):
        self.repo = repository
        self.session = session

    def preview(
        self,
        request: CheckOutRequest,
        *,
        operator: User,
    ) -> CheckOutPreviewResponse:
        """POST /check-out/preview — tính phí mà không thay đổi trạng thái phiên."""
        transaction = self._find_single_session(request, operator)
        exit_time = datetime.now(UTC)
        t_in = _normalize_tz(transaction.check_in_time)
        t_out = _normalize_tz(exit_time)
        fee, breakdown = _calculate_fee_stub(transaction, t_out, request.is_lost_ticket)
        duration_minutes = max(0, int((t_out - t_in).total_seconds() // 60))
        vtype_in = getattr(transaction, "vehicle_type", "CAR") or "CAR"
        vtype_out = request.vehicle_type_out
        mismatch = bool(vtype_out and vtype_out.upper() != vtype_in.upper())

        return CheckOutPreviewResponse(
            session_id=transaction.id,
            license_plate=transaction.license_plate,
            ticket_code=transaction.ticket_code,
            vehicle_type_in=vtype_in,
            vehicle_type_out=vtype_out,
            vehicle_type_mismatch=mismatch,
            check_in_time=transaction.check_in_time,
            check_in_image_url=transaction.image_url,
            exit_image_url=request.exit_image_url,
            duration_minutes=duration_minutes,
            fee=fee,
            price_snapshot=getattr(transaction, "price_snapshot", None),
            fee_breakdown=breakdown,
            status=transaction.status,
            message="⚠️ Lệch loại xe — cần xác nhận trước khi cho ra." if mismatch else "",
        )

    def process_checkout(
        self,
        request: CheckOutRequest,
        *,
        operator: User,
        idempotency_key: str | None = None,
    ) -> CheckOutResponse:
        """
        POST /check-out — đóng phiên gửi xe (idempotent theo key).

        Luồng:
          1. Kiểm tra idempotency_key: nếu đã COMPLETED với key này thì trả lại.
          2. Tìm phiên mở (hoặc PAID).
          3. Cảnh báo lệch loại xe (phải có override_reason nếu lệch).
          4. Tính phí:
             - Nếu fee == 0 hoặc request.payment_method được cung cấp:
               đóng phiên ngay -> COMPLETED, giảm bộ đếm (BR-14).
             - Nếu fee > 0 và chưa có phương thức thanh toán:
               chuyển sang PAYMENT_PENDING.
        """
        raw_key = idempotency_key if idempotency_key is not None else request.idempotency_key
        key = validate_idempotency_key(raw_key)

        # 1. Kiểm tra idempotent
        existing_done = self.repo.get_by_idempotency_key_checkout(key)
        if existing_done and existing_done.status in {
            TransactionStatus.COMPLETED,
            TransactionStatus.EXITED,
        }:
            from app.modules.checkin.service import CheckInService

            return CheckOutResponse(
                transaction=CheckInService.to_response(existing_done),
                fee=float(getattr(existing_done, "fee", 0.0) or 0.0),
                status=existing_done.status,
                barrier_opened=True,
                message="Phiên đã được đóng trước đó (idempotent).",
            )

        # 2. Tìm phiên
        transaction = self._find_single_session(request, operator)

        # Nếu phiên đã PAID trước đó
        if transaction.status == TransactionStatus.PAID:
            return self._complete_session(
                transaction, request, operator, fee=float(transaction.fee or 0.0), key=key
            )

        # 3. Kiểm tra làn ra
        exit_lane = self.session.get(Lane, request.exit_lane_id)
        if exit_lane is None:
            raise AppError(status_code=404, code="LANE_NOT_FOUND", message="Làn ra không tồn tại.")
        if not exit_lane.is_active:
            raise AppError(
                status_code=400, code="LANE_INACTIVE", message="Làn ra đang không hoạt động."
            )
        if exit_lane.direction != LaneDirection.OUT:
            raise AppError(
                status_code=400,
                code="INVALID_LANE_TYPE",
                message="Check-out chỉ được thực hiện trên làn OUT.",
            )

        lane_building_id = getattr(exit_lane, "building_id", None)
        tx_building_id = getattr(transaction, "building_id", None)
        if (
            lane_building_id is not None
            and tx_building_id is not None
            and lane_building_id != tx_building_id
        ):
            raise AppError(
                status_code=400,
                code="BUILDING_MISMATCH",
                message="Làn ra thuộc tòa nhà khác với phiên gửi xe.",
            )

        # Cảnh báo lệch loại xe
        vtype_in = getattr(transaction, "vehicle_type", "CAR") or "CAR"
        vtype_out = request.vehicle_type_out
        mismatch = bool(vtype_out and vtype_out.upper() != vtype_in.upper())
        if mismatch and not request.override_reason:
            raise AppError(
                status_code=409,
                code="VEHICLE_TYPE_MISMATCH",
                message=(
                    f"Loại xe ra ({vtype_out}) khác loại xe vào ({vtype_in}). "
                    "Cung cấp override_reason để xác nhận."
                ),
                details={"vehicle_type_in": vtype_in, "vehicle_type_out": vtype_out},
            )

        # 4. Tính phí
        exit_time = datetime.now(UTC)
        fee, breakdown = _calculate_fee_stub(transaction, exit_time, request.is_lost_ticket)

        try:
            # Nếu miễn phí hoặc thanh toán trực tiếp tại cổng
            if fee == 0.0 or request.payment_method:
                if request.payment_method and fee > 0.0:
                    record_lifecycle_event(
                        session=self.session,
                        session_id=transaction.id,
                        event_type=LifecycleEventType.PAYMENT_RECEIVED,
                        actor_type=ActorType.OPERATOR,
                        actor_id=operator.id,
                        lane_id=request.exit_lane_id,
                        building_id=tx_building_id,
                        details={"payment_method": request.payment_method, "amount": fee},
                    )
                return self._complete_session(transaction, request, operator, fee=fee, key=key)
            else:
                # Phí > 0 và chưa trả: chuyển sang PAYMENT_PENDING
                transaction.status = TransactionStatus.PAYMENT_PENDING
                transaction.fee = fee
                transaction.exit_lane_id = request.exit_lane_id
                transaction.exit_time = exit_time
                existing_notes = transaction.notes or ""
                if f"[CHECKOUT_KEY:{key}]" not in existing_notes:
                    transaction.notes = (
                        f"{existing_notes}\n[CHECKOUT_KEY:{key}]".strip()
                        if existing_notes
                        else f"[CHECKOUT_KEY:{key}]"
                    )

                record_lifecycle_event(
                    session=self.session,
                    session_id=transaction.id,
                    event_type=LifecycleEventType.FEE_CALCULATED,
                    actor_type=ActorType.SYSTEM,
                    actor_id=operator.id,
                    lane_id=request.exit_lane_id,
                    building_id=tx_building_id,
                    details={
                        "fee": fee,
                        "breakdown": breakdown,
                        "is_lost_ticket": request.is_lost_ticket,
                    },
                )
                log_action(
                    db=self.session,
                    user_id=operator.id,
                    action="CHECKOUT_FEE_CALCULATED",
                    entity_type="ParkingTransaction",
                    entity_id=str(transaction.id),
                    new_value={"fee": fee, "status": TransactionStatus.PAYMENT_PENDING},
                )
                self.session.flush()
                self.session.commit()
                self.session.refresh(transaction)

                from app.modules.checkin.service import CheckInService

                return CheckOutResponse(
                    transaction=CheckInService.to_response(transaction),
                    fee=fee,
                    status=TransactionStatus.PAYMENT_PENDING,
                    barrier_opened=False,
                    vehicle_type_mismatch=mismatch,
                    message=f"Phí {fee:,.0f}đ. Vui lòng thu tiền để hoàn tất check-out.",
                )
        except Exception:
            self.session.rollback()
            raise

    def _complete_session(
        self,
        transaction: ParkingTransaction,
        request: CheckOutRequest,
        operator: User,
        fee: float,
        key: str | None = None,
    ) -> CheckOutResponse:
        """
        Hoàn tất phiên gửi xe trong cùng 1 transaction (BR-14):
          - Cập nhật trạng thái: EXITED -> COMPLETED
          - Ghi lifecycle: EXIT_CONFIRMED, BARRIER_OPENED_OUT, COMPLETED
          - Mở barrier mô phỏng (BR-23)
          - Giảm bộ đếm nguyên tử qua CounterService.decrement_atomic()
        """
        exit_time = datetime.now(UTC)
        tx_building_id = getattr(transaction, "building_id", None)
        vtype = getattr(transaction, "vehicle_type", "CAR") or "CAR"
        vtype_out = request.vehicle_type_out
        mismatch = bool(vtype_out and vtype_out.upper() != vtype.upper())

        transaction.status = TransactionStatus.EXITED
        transaction.exit_time = exit_time
        transaction.exit_lane_id = request.exit_lane_id
        transaction.fee = fee

        # Ghi nhận checkout key & exit image vào notes để idempotent
        existing_notes = transaction.notes or ""
        notes_parts = [existing_notes] if existing_notes else []
        if key and f"[CHECKOUT_KEY:{key}]" not in existing_notes:
            notes_parts.append(f"[CHECKOUT_KEY:{key}]")
        if (
            request.exit_image_url
            and f"[EXIT_IMAGE:{request.exit_image_url}]" not in existing_notes
        ):
            notes_parts.append(f"[EXIT_IMAGE:{request.exit_image_url}]")
        transaction.notes = "\n".join(notes_parts) if notes_parts else None

        record_lifecycle_event(
            session=self.session,
            session_id=transaction.id,
            event_type=LifecycleEventType.EXIT_CONFIRMED,
            actor_type=ActorType.OPERATOR,
            actor_id=operator.id,
            lane_id=request.exit_lane_id,
            building_id=tx_building_id,
            details={
                "exit_time": exit_time.isoformat(),
                "fee": fee,
                "vehicle_type_out": vtype_out,
                "mismatch": mismatch,
                "override_reason": request.override_reason,
            },
            image_ref=request.exit_image_url,
        )

        exit_lane = self.session.get(Lane, request.exit_lane_id)
        barrier_id = getattr(exit_lane, "barrier_id", None) if exit_lane else None
        trigger_reason = (
            BarrierTriggerReason.OVERRIDE
            if request.override_reason
            else BarrierTriggerReason.NORMAL
        )
        record_barrier_event(
            db=self.session,
            lane_id=request.exit_lane_id,
            building_id=tx_building_id,
            barrier_id=barrier_id,
            action=BarrierAction.OPEN,
            trigger_reason=trigger_reason,
            operator_id=operator.id if operator else None,
            session_id=transaction.id,
            status=BarrierStatus.OPEN,
            details={
                "barrier_id": barrier_id,
                "trigger_reason": trigger_reason,
                "override_reason": request.override_reason,
                "source": "CHECK_OUT",
                "fee": fee,
            },
        )
        barrier_opened = True

        record_lifecycle_event(
            session=self.session,
            session_id=transaction.id,
            event_type=LifecycleEventType.BARRIER_OPENED_OUT,
            actor_type=ActorType.SYSTEM,
            actor_id=operator.id,
            lane_id=request.exit_lane_id,
            building_id=tx_building_id,
            details={
                "barrier_id": barrier_id,
                "opened": barrier_opened,
                "trigger_reason": trigger_reason,
                "override_reason": request.override_reason,
            },
        )

        transaction.status = TransactionStatus.COMPLETED

        record_lifecycle_event(
            session=self.session,
            session_id=transaction.id,
            event_type=LifecycleEventType.COMPLETED,
            actor_type=ActorType.SYSTEM,
            actor_id=operator.id,
            lane_id=request.exit_lane_id,
            building_id=tx_building_id,
            details={
                "fee": fee,
                "exit_lane_id": str(request.exit_lane_id),
                "vehicle_type": vtype,
            },
        )

        # Giảm bộ đếm nguyên tử trong cùng transaction (BR-14)
        CounterService.decrement_atomic(
            db=self.session,
            building_id=tx_building_id,
            vehicle_type=vtype,
            session_id=transaction.id,
            actor_type=ActorType.OPERATOR,
            actor_id=operator.id,
            reason="CHECK_OUT",
        )

        log_action(
            db=self.session,
            user_id=operator.id,
            action="CHECKOUT_COMPLETED",
            entity_type="ParkingTransaction",
            entity_id=str(transaction.id),
            new_value={
                "exit_time": exit_time.isoformat(),
                "fee": fee,
                "exit_lane_id": str(request.exit_lane_id),
                "status": TransactionStatus.COMPLETED,
            },
        )

        self.session.flush()
        self.session.commit()
        self.session.refresh(transaction)

        from app.modules.checkin.service import CheckInService

        return CheckOutResponse(
            transaction=CheckInService.to_response(transaction),
            fee=fee,
            status=TransactionStatus.COMPLETED,
            barrier_opened=barrier_opened,
            vehicle_type_mismatch=mismatch,
            message="Xe đã ra thành công." + (" (Lệch loại xe — đã override.)" if mismatch else ""),
        )

    def _find_single_session(
        self,
        request: CheckOutRequest,
        operator: User,
    ) -> ParkingTransaction:
        """
        Tìm duy nhất một phiên mở có thể checkout:
          - Theo request.session_id nếu có
          - Theo mã vé (xe đạp)
          - Theo biển số chuẩn hóa
        Xử lý ngoại lệ: 404 nếu không tìm thấy, 409 nếu trùng nhiều phiên.
        """
        building_id: UUID | None = getattr(operator, "building_id", None)
        if not isinstance(building_id, UUID):
            building_id = None

        sessions: list[ParkingTransaction] = []

        if request.session_id:
            tx = self.repo.get_by_id(request.session_id)
            if tx and (building_id is None or getattr(tx, "building_id", None) == building_id):
                sessions = [tx]
        elif request.ticket_code:
            sessions = self.repo.get_checkout_eligible_by_ticket(
                request.ticket_code.strip().upper(), building_id
            )
        elif request.license_plate:
            normalized = normalize_plate(request.license_plate)
            sessions = self.repo.get_checkout_eligible_by_plate(normalized, building_id)

        if not sessions:
            raise AppError(
                status_code=404,
                code="SESSION_NOT_FOUND",
                message=(
                    "Không tìm thấy phiên gửi xe đang mở. "
                    "Bảo vệ cần đối chiếu ảnh cổng vào và tạo phiên bù nếu cần."
                ),
                details={
                    "license_plate": request.license_plate,
                    "ticket_code": request.ticket_code,
                    "session_id": str(request.session_id) if request.session_id else None,
                },
            )

        if len(sessions) > 1:
            ids = [str(s.id) for s in sessions]
            log_action(
                db=self.session,
                user_id=operator.id,
                action="DATA_INTEGRITY_ALERT",
                entity_type="ParkingTransaction",
                entity_id=ids[0],
                new_value={
                    "alert": "DUPLICATE_ACTIVE_SESSIONS",
                    "session_ids": ids,
                    "license_plate": request.license_plate,
                    "ticket_code": request.ticket_code,
                },
            )
            raise AppError(
                status_code=409,
                code="DUPLICATE_ACTIVE_SESSIONS",
                message="Phát hiện nhiều phiên mở cùng biển số/vé. Chuyển bảo vệ xử lý thủ công.",
                details={"session_ids": ids},
            )

        transaction = sessions[0]

        if transaction.status not in _CHECKOUT_ELIGIBLE:
            raise AppError(
                status_code=409,
                code="INVALID_SESSION_STATUS",
                message=f"Phiên ở trạng thái {transaction.status} không thể thực hiện check-out.",
                details={"session_id": str(transaction.id), "status": transaction.status},
            )

        return transaction

    def record_payment(
        self,
        session_id: UUID,
        *,
        operator: User,
        payment_method: str,
        amount: float,
        provider_ref: str | None = None,
        override_reason: str | None = None,
    ) -> CheckOutResponse:
        """
        Ghi nhận thanh toán cho phiên PAYMENT_PENDING -> PAID -> COMPLETED.
        """
        tx = self.session.get(ParkingTransaction, session_id)
        if tx is None:
            raise AppError(
                status_code=404, code="SESSION_NOT_FOUND", message="Không tìm thấy phiên gửi xe."
            )
        if tx.status not in {TransactionStatus.PAYMENT_PENDING, TransactionStatus.PAID}:
            raise AppError(
                status_code=409,
                code="INVALID_SESSION_STATUS",
                message=f"Phiên ở trạng thái {tx.status} không thể ghi nhận thanh toán.",
            )

        tx_building_id = getattr(tx, "building_id", None)
        tx.status = TransactionStatus.PAID

        record_lifecycle_event(
            session=self.session,
            session_id=tx.id,
            event_type=LifecycleEventType.PAYMENT_RECEIVED,
            actor_type=ActorType.OPERATOR,
            actor_id=operator.id,
            building_id=tx_building_id,
            details={
                "payment_method": payment_method,
                "amount": amount,
                "provider_ref": provider_ref,
                "override_reason": override_reason,
            },
        )
        log_action(
            db=self.session,
            user_id=operator.id,
            action="PAYMENT_RECEIVED",
            entity_type="ParkingTransaction",
            entity_id=str(tx.id),
            new_value={
                "payment_method": payment_method,
                "amount": amount,
                "provider_ref": provider_ref,
            },
        )
        self.session.flush()

        if tx.exit_lane_id is None:
            raise AppError(
                status_code=422,
                code="EXIT_LANE_MISSING",
                message="Phiên chưa có làn ra. Vui lòng gọi lại POST /check-out trước.",
            )

        dummy_request = CheckOutRequest(
            session_id=tx.id,
            license_plate=tx.license_plate,
            ticket_code=tx.ticket_code,
            exit_lane_id=tx.exit_lane_id,
            override_reason=override_reason,
        )
        return self._complete_session(tx, dummy_request, operator, fee=float(tx.fee or 0.0))
