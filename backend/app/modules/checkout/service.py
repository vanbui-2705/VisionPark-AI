from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
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
from app.modules.pricing.domain import (
    AccessDecision,
    AccessResult,
    PriceSnapshot,
    TicketEntitlement,
    TicketKind,
    calculate_fee,
    check_ticket_access,
)
from app.modules.pricing.models import Subscription, TicketProduct, Vehicle
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


DEFAULT_BUILDING_UUID = UUID("00000000-0000-0000-0000-000000000001")


def _build_price_snapshot_from_tx(transaction: ParkingTransaction) -> PriceSnapshot:
    """Đọc snapshot từ phiên gửi xe, fallback an toàn nếu là dữ liệu test cũ (BR-13)."""
    raw = getattr(transaction, "price_snapshot", None)
    if isinstance(raw, dict) and "version_id" in raw and "initial_fee" in raw:
        return PriceSnapshot.model_validate(raw)

    free_mins = raw.get("free_minutes", 0) if isinstance(raw, dict) else 0
    rate = raw.get("rate_per_hour", 5000.0) if isinstance(raw, dict) else 5000.0
    lost_fee = raw.get("lost_ticket_fee", 50000.0) if isinstance(raw, dict) else 50000.0
    building_id = getattr(transaction, "building_id", None) or DEFAULT_BUILDING_UUID

    return PriceSnapshot(
        version_id=building_id,
        rule_id=DEFAULT_BUILDING_UUID,
        vehicle_type=getattr(transaction, "vehicle_type", "CAR") or "CAR",
        ticket_kind=TicketKind.HOURLY,
        customer_class="STANDARD",
        free_minutes=int(free_mins),
        initial_minutes=60,
        initial_fee=int(rate),
        block_minutes=60,
        block_fee=int(rate),
        lost_ticket_fee=int(lost_fee),
    )


def verify_ticket_entitlement_for_checkout(
    db: Session,
    transaction: ParkingTransaction,
    exit_time: datetime,
) -> tuple[AccessResult | None, datetime | None]:
    """Kiểm tra quyền vé tháng/vé ngày tại thời điểm ra cổng (M4)."""
    building_id = transaction.building_id
    if not building_id:
        return None, None

    plate = transaction.normalized_plate or transaction.license_plate
    code = transaction.ticket_code

    stmt = select(Vehicle).where(Vehicle.building_id == building_id)
    if code:
        stmt = stmt.where(Vehicle.ticket_code == code.strip().upper())
    elif plate:
        stmt = stmt.where(Vehicle.normalized_plate == normalize_plate(plate))
    else:
        return None, None

    vehicle = db.scalar(stmt)
    if not vehicle:
        return None, None

    sub = db.scalar(
        select(Subscription)
        .where(
            Subscription.building_id == building_id,
            Subscription.vehicle_id == vehicle.id,
        )
        .order_by(Subscription.valid_until.desc())
    )
    if not sub:
        return None, None

    product = db.get(TicketProduct, sub.product_id)
    if not product or not product.active:
        return None, None

    entitlement = TicketEntitlement(
        kind=TicketKind(product.kind),
        plate=vehicle.normalized_plate,
        ticket_code=vehicle.ticket_code,
        zone_id=sub.zone_id,
        valid_from=_normalize_tz(sub.valid_from),
        valid_until=_normalize_tz(sub.valid_until),
        grace_days=sub.grace_days,
    )
    result = check_ticket_access(
        ticket=entitlement,
        at=_normalize_tz(exit_time),
        plate=plate,
        ticket_code=code,
        zone_id=getattr(transaction, "assigned_zone_id", None) or sub.zone_id,
    )
    return result, entitlement.valid_until


def calculate_parking_fee(
    transaction: ParkingTransaction,
    exit_time: datetime,
    is_lost_ticket: bool = False,
    session: Session | None = None,
) -> tuple[float, list[dict], dict]:
    """
    Tính phí theo bản chụp giá (price_snapshot) của phiên gửi xe (BR-13, P3-M3-09).

    Đảm bảo: đổi giá giữa chừng không làm đổi phí của xe đang trong bãi.
    """
    snapshot = _build_price_snapshot_from_tx(transaction)
    t_in = _normalize_tz(transaction.check_in_time)
    t_out = _normalize_tz(exit_time)

    # Nếu có session DB, kiểm tra quyền vé (subscription) mới nhất
    if session is not None and snapshot.ticket_kind in {TicketKind.HOURLY, TicketKind.MONTHLY}:
        access_res, valid_until = verify_ticket_entitlement_for_checkout(
            session, transaction, t_out
        )
        if access_res and access_res.decision == AccessDecision.ALLOW and valid_until:
            snapshot = snapshot.model_copy(
                update={
                    "ticket_kind": TicketKind.MONTHLY,
                    "entitlement_valid_until": valid_until,
                }
            )
        elif access_res and access_res.decision == AccessDecision.DENY:
            snapshot = snapshot.model_copy(
                update={
                    "ticket_kind": TicketKind.HOURLY,
                    "entitlement_valid_until": None,
                }
            )

    fee_res = calculate_fee(
        check_in=t_in,
        check_out=t_out,
        snapshot=snapshot,
        lost_ticket=is_lost_ticket,
    )
    lines_dump = [line.model_dump() for line in fee_res.lines]
    duration_mins = max(0, int((t_out - t_in).total_seconds() // 60))
    breakdown = {
        "duration_minutes": duration_mins,
        "price_version_id": str(fee_res.price_version_id),
        "total": fee_res.total,
        "currency": fee_res.currency,
        "lines": lines_dump,
    }
    return float(fee_res.total), lines_dump, breakdown


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
        fee, lines, breakdown = calculate_parking_fee(
            transaction, t_out, request.is_lost_ticket, session=self.session
        )
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
            fee_lines=lines,
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
            fee, lines, breakdown = calculate_parking_fee(
                transaction, datetime.now(UTC), request.is_lost_ticket, session=self.session
            )
            return self._complete_session(
                transaction,
                request,
                operator,
                fee=float(transaction.fee or 0.0),
                key=key,
                fee_lines=lines,
                fee_breakdown=breakdown,
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
        fee, lines, breakdown = calculate_parking_fee(
            transaction, exit_time, request.is_lost_ticket, session=self.session
        )

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
                return self._complete_session(
                    transaction,
                    request,
                    operator,
                    fee=fee,
                    key=key,
                    fee_lines=lines,
                    fee_breakdown=breakdown,
                )
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
                        "lines": lines,
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
                    fee_lines=lines,
                    fee_breakdown=breakdown,
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
        fee_lines: list[dict] | None = None,
        fee_breakdown: dict | None = None,
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
                "lines": fee_lines,
                "breakdown": fee_breakdown,
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
            fee_lines=fee_lines,
            fee_breakdown=fee_breakdown,
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
