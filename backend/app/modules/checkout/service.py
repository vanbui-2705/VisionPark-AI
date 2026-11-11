from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.database.idempotency import (
    IdempotencyOperation,
    encode_checkout_idempotency_tag,
    fingerprint_payload,
    require_matching_fingerprint,
    resolve_idempotency_key,
    validate_idempotency_key,
    verify_checkout_idempotency,
)
from app.modules.alpr.models import Detection
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
from app.modules.pricing.models import (
    Invoice,
    Payment,
    PricingVersion,
    Subscription,
    TicketProduct,
    Vehicle,
)
from app.modules.users.models import User

from .schemas import (
    ALLOWED_CHECKOUT_PAYMENT_METHODS,
    ALLOWED_SESSION_PAYMENT_METHODS,
    CheckOutPreviewResponse,
    CheckOutRequest,
    CheckOutResponse,
)

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


def _is_admin_operator(operator: User | None) -> bool:
    """Kiểm tra người dùng có quyền quản trị (SYSTEM_ADMIN / BUILDING_ADMIN) để override phí."""
    if operator is None:
        return False
    role_obj = getattr(operator, "role", None)
    role_name = getattr(role_obj, "name", None) or getattr(operator, "role_name", None)
    return str(role_name or "").upper() in {"SYSTEM_ADMIN", "BUILDING_ADMIN", "ADMIN"}


def _compute_checkout_fingerprint(request: CheckOutRequest, norm_method: str | None) -> str:
    """Tạo fingerprint cho request checkout để phát hiện tái sử dụng key khác payload (BUILD-01)."""
    if request.session_id:
        ident = f"session:{request.session_id}"
    elif request.ticket_code:
        ident = f"ticket:{request.ticket_code.strip().upper()}"
    else:
        ident = f"plate:{normalize_plate(request.license_plate or '')}"

    return fingerprint_payload(
        {
            "ident": ident,
            "exit_lane_id": str(request.exit_lane_id),
            "payment_method": norm_method,
            "is_lost_ticket": bool(request.is_lost_ticket),
            "vehicle_type_out": (request.vehicle_type_out or "").strip().upper() or None,
        }
    )


def _build_price_snapshot_from_tx(transaction: ParkingTransaction) -> PriceSnapshot:
    """Đọc snapshot từ phiên gửi xe, fallback an toàn nếu là dữ liệu test cũ (BR-13)."""
    raw = getattr(transaction, "price_snapshot", None)
    if isinstance(raw, dict) and "version_id" in raw and "initial_fee" in raw:
        return PriceSnapshot.model_validate(raw)

    free_mins = raw.get("free_minutes", 15) if isinstance(raw, dict) else 15
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
    formula_parts = [
        f"{line['code']}: {line['amount']:,.0f}đ"
        + (f" (x{line['quantity']})" if line.get("quantity", 1) > 1 else "")
        for line in lines_dump
    ]
    formula_str = " + ".join(formula_parts) if formula_parts else "Miễn phí (0đ)"
    breakdown = {
        "duration_minutes": duration_mins,
        "price_version_id": str(fee_res.price_version_id),
        "total": round(fee_res.total, 0),
        "currency": fee_res.currency,
        "lines": lines_dump,
        "formula": formula_str,
    }
    return float(round(fee_res.total, 0)), lines_dump, breakdown


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
        if transaction.status == TransactionStatus.PAID:
            fee, lines, breakdown = float(transaction.fee or 0.0), [], None
        else:
            fee, lines, breakdown = calculate_parking_fee(
                transaction, t_out, request.is_lost_ticket, session=self.session
            )
        duration_minutes = max(0, int((t_out - t_in).total_seconds() // 60))
        vtype_in = getattr(transaction, "vehicle_type", "CAR") or "CAR"
        vtype_out = request.vehicle_type_out
        mismatch = bool(vtype_out and vtype_out.upper() != vtype_in.upper())

        check_in_img = transaction.image_url
        if not check_in_img and transaction.detection_id:
            det = transaction.detection or self.session.get(Detection, transaction.detection_id)
            if det and getattr(det, "image_key", None):
                check_in_img = f"/api/v1/alpr/media/{det.image_key}"
            else:
                check_in_img = f"/api/v1/detections/{transaction.detection_id}/image"

        if request.is_lost_ticket:
            lost_fee_amount = next(
                (
                    float(line.get("amount", 0.0))
                    for line in lines
                    if line.get("code") == "LOST_TICKET"
                ),
                float(getattr(_build_price_snapshot_from_tx(transaction), "lost_ticket_fee", 0.0)),
            )
            log_action(
                db=self.session,
                user_id=operator.id,
                action="LOST_TICKET_PREVIEW",
                entity_type="ParkingTransaction",
                entity_id=str(transaction.id),
                new_value={
                    "is_lost_ticket": True,
                    "lost_ticket_fee": lost_fee_amount,
                    "fee": fee,
                },
            )

        return CheckOutPreviewResponse(
            session_id=transaction.id,
            license_plate=transaction.license_plate,
            ticket_code=transaction.ticket_code,
            vehicle_type_in=vtype_in,
            vehicle_type_out=vtype_out,
            vehicle_type_mismatch=mismatch,
            check_in_time=t_in,
            exit_time=t_out,
            check_in_image_url=check_in_img,
            exit_image_url=request.exit_image_url,
            duration_minutes=duration_minutes,
            fee=round(fee, 0),
            price_snapshot=getattr(transaction, "price_snapshot", None),
            fee_lines=lines,
            fee_breakdown=breakdown,
            status=transaction.status,
            message="⚠️ Lệch loại xe — cần xác nhận trước khi cho ra." if mismatch else "",
        )

    def _replay_from_idempotency_record(
        self,
        record_tx_id: UUID | None,
        record_status: str,
        payload: dict | None,
        *,
        fallback_tx: ParkingTransaction | None = None,
    ) -> CheckOutResponse | None:
        """Tái tạo CheckOutResponse từ bản ghi IdempotencyRecord đã lưu (BUILD-01)."""
        tx = fallback_tx or (self.repo.get_by_id(record_tx_id) if record_tx_id else None)
        if tx is None and record_tx_id is not None:
            tx = self.session.get(ParkingTransaction, record_tx_id)
        if tx is None:
            return None

        from app.modules.checkin.service import CheckInService

        data = payload or {}
        existing_inv = self.session.scalar(select(Invoice).where(Invoice.transaction_id == tx.id))
        existing_pay = (
            self.session.scalar(
                select(Payment).where(
                    Payment.invoice_id == existing_inv.id, Payment.status == "PAID"
                )
            )
            if existing_inv
            else None
        )
        inv_id_raw = data.get("invoice_id")
        pay_id_raw = data.get("payment_id")
        inv_id = (
            UUID(str(inv_id_raw)) if inv_id_raw else (existing_inv.id if existing_inv else None)
        )
        pay_id = (
            UUID(str(pay_id_raw)) if pay_id_raw else (existing_pay.id if existing_pay else None)
        )
        effective_status = (
            tx.status
            if tx.status in {TransactionStatus.COMPLETED, TransactionStatus.EXITED}
            else TransactionStatus(record_status)
        )
        is_completed = effective_status in {TransactionStatus.COMPLETED, TransactionStatus.EXITED}
        return CheckOutResponse(
            transaction=CheckInService.to_response(tx),
            fee=float(data.get("fee", getattr(tx, "fee", 0.0) or 0.0)),
            fee_lines=data.get("fee_lines"),
            fee_breakdown=data.get("fee_breakdown"),
            status=effective_status,
            barrier_opened=bool(data.get("barrier_opened", is_completed)),
            barrier_event_recorded=bool(data.get("barrier_event_recorded", is_completed)),
            barrier_mode=str(data.get("barrier_mode", "SIMULATED")),
            vehicle_type_mismatch=bool(data.get("vehicle_type_mismatch", False)),
            invoice_id=inv_id,
            payment_id=pay_id,
            message=(
                "Phiên đã được đóng trước đó (idempotent)."
                if is_completed
                else str(
                    data.get(
                        "message",
                        f"Phí {float(getattr(tx, 'fee', 0.0) or 0.0):,.0f}đ. "
                        "Vui lòng thu tiền để hoàn tất check-out.",
                    )
                )
            ),
        )

    def process_checkout(
        self,
        request: CheckOutRequest,
        *,
        operator: User,
        idempotency_key: str | None = None,
    ) -> CheckOutResponse:
        """
        POST /check-out — đóng phiên gửi xe (idempotent theo key + fingerprint).

        Luồng:
          1. Kiểm tra payment_method hợp lệ (DEMO-01 / IMPROVE-01).
          2. Kiểm tra idempotency_key & fingerprint (BUILD-01):
             - Cùng key + cùng payload -> trả lại kết quả cũ.
             - Cùng key + khác payload -> trả 409 IDEMPOTENCY_KEY_REUSED.
          3. Tìm phiên mở (hoặc PAID).
          4. Cảnh báo lệch loại xe (phải có override_reason nếu lệch).
          5. Tính phí & đồng bộ sổ Invoice/Payment (BUILD-02 / DEMO-03).
        """
        key = resolve_idempotency_key(idempotency_key, request.idempotency_key)

        norm_method = (
            str(request.payment_method).strip().upper() if request.payment_method else None
        )
        if norm_method is not None and norm_method not in ALLOWED_CHECKOUT_PAYMENT_METHODS:
            raise AppError(
                status_code=422,
                code="INVALID_PAYMENT_METHOD",
                message=(
                    f"Phương thức thanh toán '{request.payment_method}' không được hỗ trợ "
                    f"tại trạm. Chỉ chấp nhận: "
                    f"{', '.join(sorted(ALLOWED_CHECKOUT_PAYMENT_METHODS))}."
                ),
            )

        checkout_fp = _compute_checkout_fingerprint(request, norm_method)
        operator_building_id = getattr(operator, "building_id", None)
        if not isinstance(operator_building_id, UUID):
            operator_building_id = None

        # 1. Kiểm tra bảng IdempotencyRecord trước (BUILD-01), fallback về legacy lookup
        existing_record = self.repo.get_operation_idempotency_record(
            IdempotencyOperation.CHECKOUT, key, operator_building_id
        )
        if existing_record is not None:
            require_matching_fingerprint(existing_record.request_fingerprint, checkout_fp)
            replayed = self._replay_from_idempotency_record(
                existing_record.transaction_id,
                existing_record.status,
                existing_record.response_payload,
            )
            if replayed is not None:
                return replayed

        existing_done = self.repo.get_by_idempotency_key_checkout(key)
        if existing_done and existing_done.status in {
            TransactionStatus.COMPLETED,
            TransactionStatus.EXITED,
        }:
            verify_checkout_idempotency(existing_done.notes, key, checkout_fp)
            replayed_legacy = self._replay_from_idempotency_record(
                existing_done.id,
                str(existing_done.status),
                None,
                fallback_tx=existing_done,
            )
            if replayed_legacy is not None:
                return replayed_legacy

        # 2. Tìm phiên (khóa dòng cấp DB để chống đua song song - BUILD-01)
        transaction = self._find_single_session(request, operator, lock=True)

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
                checkout_fingerprint=checkout_fp,
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

        if request.expected_fee is not None and request.expected_fee != fee:
            raise AppError(
                status_code=409,
                code="FEE_CHANGED",
                message="Phí gửi xe đã thay đổi. Cập nhật phí và xác nhận lại trước khi thu tiền.",
                details={"expected_fee": request.expected_fee, "fee": fee},
            )

        try:
            # Nếu miễn phí hoặc thanh toán trực tiếp tại cổng (CASH 1 chạm)
            if fee == 0.0 or norm_method:
                if norm_method and fee > 0.0:
                    record_lifecycle_event(
                        session=self.session,
                        session_id=transaction.id,
                        event_type=LifecycleEventType.PAYMENT_RECEIVED,
                        actor_type=ActorType.OPERATOR,
                        actor_id=operator.id,
                        lane_id=request.exit_lane_id,
                        building_id=tx_building_id,
                        details={"payment_method": norm_method, "amount": fee},
                    )
                    log_action(
                        db=self.session,
                        user_id=operator.id,
                        action="PAYMENT_RECEIVED",
                        entity_type="ParkingTransaction",
                        entity_id=str(transaction.id),
                        new_value={
                            "payment_method": norm_method,
                            "amount": fee,
                            "source": "CHECK_OUT_DIRECT",
                        },
                    )
                return self._complete_session(
                    transaction,
                    request,
                    operator,
                    fee=fee,
                    key=key,
                    checkout_fingerprint=checkout_fp,
                    fee_lines=lines,
                    fee_breakdown=breakdown,
                )
            else:
                # Phí > 0 và chưa trả: chuyển sang PAYMENT_PENDING & tạo Invoice PENDING (BUILD-02)
                transaction.status = TransactionStatus.PAYMENT_PENDING
                transaction.fee = fee
                transaction.exit_lane_id = request.exit_lane_id
                transaction.exit_time = exit_time
                existing_notes = transaction.notes or ""
                idemp_tag = encode_checkout_idempotency_tag(key, checkout_fp)
                if f"[CHECKOUT_KEY:{key}]" not in existing_notes:
                    transaction.notes = (
                        f"{existing_notes}\n{idemp_tag}".strip() if existing_notes else idemp_tag
                    )

                invoice_id, _ = self._sync_checkout_ledger(
                    transaction,
                    request=request,
                    operator=operator,
                    exit_time=exit_time,
                    fee=fee,
                    fee_lines=lines,
                    key=key,
                    invoice_status_override="PENDING",
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
                        "invoice_id": str(invoice_id),
                    },
                )
                log_action(
                    db=self.session,
                    user_id=operator.id,
                    action="CHECKOUT_FEE_CALCULATED",
                    entity_type="ParkingTransaction",
                    entity_id=str(transaction.id),
                    new_value={
                        "fee": fee,
                        "status": TransactionStatus.PAYMENT_PENDING,
                        "invoice_id": str(invoice_id),
                    },
                )
                pending_message = f"Phí {fee:,.0f}đ. Vui lòng thu tiền để hoàn tất check-out."
                self.repo.save_operation_idempotency_record(
                    building_id=tx_building_id,
                    operation=IdempotencyOperation.CHECKOUT,
                    key=key,
                    request_fingerprint=checkout_fp,
                    transaction_id=transaction.id,
                    status=TransactionStatus.PAYMENT_PENDING,
                    response_payload={
                        "fee": fee,
                        "fee_lines": lines,
                        "fee_breakdown": breakdown,
                        "status": TransactionStatus.PAYMENT_PENDING,
                        "barrier_opened": False,
                        "barrier_event_recorded": False,
                        "barrier_mode": "SIMULATED",
                        "vehicle_type_mismatch": mismatch,
                        "invoice_id": str(invoice_id),
                        "payment_id": None,
                        "message": pending_message,
                    },
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
                    barrier_event_recorded=False,
                    barrier_mode="SIMULATED",
                    vehicle_type_mismatch=mismatch,
                    invoice_id=invoice_id,
                    message=pending_message,
                )
        except Exception:
            self.session.rollback()
            raise

    def _resolve_price_version_id(
        self,
        transaction: ParkingTransaction,
        building_id: UUID,
        operator: User,
    ) -> UUID:
        """Đảm bảo price_version_id trỏ tới một bản ghi hợp lệ trong bảng pricing_versions."""
        snapshot = _build_price_snapshot_from_tx(transaction)
        candidate = self.session.get(PricingVersion, snapshot.version_id)
        if candidate is not None:
            return candidate.id

        latest_id = self.session.scalar(
            select(PricingVersion.id)
            .where(PricingVersion.building_id == building_id)
            .order_by(PricingVersion.version_number.desc())
            .limit(1)
        )
        if latest_id is not None:
            return latest_id

        version = PricingVersion(
            id=uuid4(),
            building_id=building_id,
            version_number=1,
            active_from=datetime(2099, 1, 1, tzinfo=UTC),
            created_by_id=operator.id,
        )
        self.session.add(version)
        self.session.flush()
        return version.id

    def _sync_checkout_ledger(
        self,
        transaction: ParkingTransaction,
        *,
        request: CheckOutRequest,
        operator: User,
        exit_time: datetime,
        fee: float,
        fee_lines: list[dict] | None,
        key: str | None,
        provider_ref: str | None = None,
        invoice_status_override: str | None = None,
    ) -> tuple[UUID, UUID | None]:
        """
        BUILD-02 / DEMO-03: Đồng bộ sổ Invoice và Payment trong cùng transaction với Checkout.
        Đảm bảo:
          - Mọi phiên COMPLETED đều có đúng 1 Invoice (phục vụ M5 đếm lượt ra).
          - Mọi phiên có phí > 0 thanh toán CASH / VIETQR_MOCK đều có đúng 1 Payment trạng thái PAID
            (phục vụ M5 tổng hợp doanh thu ca/ngày).
          - Retry idempotent không tạo bản ghi Invoice/Payment trùng.
        """
        building_id = getattr(transaction, "building_id", None) or DEFAULT_BUILDING_UUID
        price_version_id = self._resolve_price_version_id(transaction, building_id, operator)
        norm_method = (
            str(request.payment_method).strip().upper() if request.payment_method else None
        )
        total_vnd = max(0, int(round(fee)))
        if invoice_status_override:
            inv_status = invoice_status_override
        else:
            inv_status = "WAIVED" if norm_method == "OVERRIDE" else "PAID"

        invoice = self.session.scalar(
            select(Invoice).where(Invoice.transaction_id == transaction.id)
        )
        if invoice is None:
            invoice = Invoice(
                building_id=building_id,
                transaction_id=transaction.id,
                price_version_id=price_version_id,
                status=inv_status,
                check_out_time=exit_time,
                lost_ticket=bool(request.is_lost_ticket),
                overtime=False,
                extra_free_minutes=0,
                total_vnd=total_vnd,
                lines=fee_lines or [],
            )
            self.session.add(invoice)
            self.session.flush()
        else:
            invoice.status = inv_status
            invoice.check_out_time = exit_time
            invoice.lost_ticket = bool(request.is_lost_ticket)
            invoice.total_vnd = total_vnd
            if fee_lines is not None:
                invoice.lines = fee_lines
            self.session.flush()

        payment: Payment | None = self.session.scalar(
            select(Payment).where(Payment.invoice_id == invoice.id, Payment.status == "PAID")
        )
        if (
            inv_status == "PAID"
            and payment is None
            and total_vnd > 0
            and norm_method in {"CASH", "VIETQR_MOCK"}
        ):
            pay_key = (key or f"checkout-pay-{transaction.id}")[:255]
            payment = self.session.scalar(
                select(Payment).where(
                    Payment.invoice_id == invoice.id,
                    Payment.idempotency_key == pay_key,
                )
            )
            if payment is None:
                payment = Payment(
                    building_id=building_id,
                    invoice_id=invoice.id,
                    provider_ref=provider_ref,
                    idempotency_key=pay_key,
                    method=norm_method,
                    status="PAID",
                    amount_vnd=total_vnd,
                    confirmed_at=exit_time,
                )
                self.session.add(payment)
            else:
                payment.status = "PAID"
                payment.amount_vnd = total_vnd
                payment.confirmed_at = payment.confirmed_at or exit_time
            self.session.flush()

        return invoice.id, (payment.id if payment else None)

    def _complete_session(
        self,
        transaction: ParkingTransaction,
        request: CheckOutRequest,
        operator: User,
        fee: float,
        key: str | None = None,
        checkout_fingerprint: str | None = None,
        fee_lines: list[dict] | None = None,
        fee_breakdown: dict | None = None,
        provider_ref: str | None = None,
        idempotency_operation: str = IdempotencyOperation.CHECKOUT,
    ) -> CheckOutResponse:
        """
        Hoàn tất phiên gửi xe trong cùng 1 transaction nguyên tử (BR-14, BUILD-02, IMPROVE-02):
          - Cập nhật trạng thái: EXITED -> COMPLETED
          - Đồng bộ Invoice & Payment (sổ cái M4/M5)
          - Ghi lifecycle: EXIT_CONFIRMED, BARRIER_OPENED_OUT, COMPLETED
          - Mở barrier mô phỏng (BR-23, mode=SIMULATED)
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

        # Ghi nhận checkout key + fingerprint & exit image vào notes để tương thích ngược
        existing_notes = transaction.notes or ""
        notes_parts = [existing_notes] if existing_notes else []
        fp = checkout_fingerprint or _compute_checkout_fingerprint(
            request,
            str(request.payment_method).strip().upper() if request.payment_method else None,
        )
        if key:
            idemp_tag = encode_checkout_idempotency_tag(key, fp)
            if f"[CHECKOUT_KEY:{key}]" not in existing_notes:
                notes_parts.append(idemp_tag)
            elif f"[CHECKOUT_FP:{key}:" not in existing_notes:
                notes_parts.append(f"[CHECKOUT_FP:{key}:{fp}]")
        if (
            request.exit_image_url
            and f"[EXIT_IMAGE:{request.exit_image_url}]" not in existing_notes
        ):
            notes_parts.append(f"[EXIT_IMAGE:{request.exit_image_url}]")
        transaction.notes = "\n".join(notes_parts) if notes_parts else None

        # Đồng bộ Invoice & Payment (BUILD-02 / DEMO-03)
        invoice_id, payment_id = self._sync_checkout_ledger(
            transaction,
            request=request,
            operator=operator,
            exit_time=exit_time,
            fee=fee,
            fee_lines=fee_lines,
            key=key,
            provider_ref=provider_ref,
        )

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
                "invoice_id": str(invoice_id),
                "payment_id": str(payment_id) if payment_id else None,
            },
            image_ref=request.exit_image_url,
        )

        exit_lane = self.session.get(Lane, request.exit_lane_id)
        barrier_id = getattr(exit_lane, "barrier_id", None) if exit_lane else None
        norm_method = (
            str(request.payment_method).strip().upper() if request.payment_method else None
        )
        if request.override_reason:
            trigger_reason = BarrierTriggerReason.OVERRIDE
        elif (
            norm_method == "CASH"
            or transaction.status == TransactionStatus.PAID
            or (norm_method and fee > 0)
        ):
            trigger_reason = BarrierTriggerReason.PAYMENT_RECEIVED
        else:
            trigger_reason = BarrierTriggerReason.NORMAL
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
                "mode": "SIMULATED",
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
                "mode": "SIMULATED",
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
                "invoice_id": str(invoice_id),
                "payment_id": str(payment_id) if payment_id else None,
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
                "is_lost_ticket": bool(request.is_lost_ticket),
                "invoice_id": str(invoice_id),
                "payment_id": str(payment_id) if payment_id else None,
                "barrier_mode": "SIMULATED",
            },
        )

        if request.is_lost_ticket:
            lost_fee_amount = next(
                (
                    float(line.get("amount", 0.0))
                    for line in (fee_lines or [])
                    if line.get("code") == "LOST_TICKET"
                ),
                float(getattr(_build_price_snapshot_from_tx(transaction), "lost_ticket_fee", 0.0)),
            )
            log_action(
                db=self.session,
                user_id=operator.id,
                action="LOST_TICKET_PROCESSED",
                entity_type="ParkingTransaction",
                entity_id=str(transaction.id),
                new_value={
                    "is_lost_ticket": True,
                    "lost_ticket_fee": lost_fee_amount,
                    "total_fee": fee,
                    "exit_lane_id": str(request.exit_lane_id),
                    "operator_id": str(operator.id),
                },
            )

        out_message = "Xe đã ra thành công." + (
            " (Lệch loại xe — đã override.)" if mismatch else ""
        )
        if key:
            self.repo.save_operation_idempotency_record(
                building_id=tx_building_id,
                operation=idempotency_operation,
                key=key,
                request_fingerprint=fp,
                transaction_id=transaction.id,
                status=TransactionStatus.COMPLETED,
                response_payload={
                    "fee": fee,
                    "fee_lines": fee_lines,
                    "fee_breakdown": fee_breakdown,
                    "status": TransactionStatus.COMPLETED,
                    "barrier_opened": barrier_opened,
                    "barrier_event_recorded": True,
                    "barrier_mode": "SIMULATED",
                    "vehicle_type_mismatch": mismatch,
                    "invoice_id": str(invoice_id),
                    "payment_id": str(payment_id) if payment_id else None,
                    "message": out_message,
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
            barrier_event_recorded=True,
            barrier_mode="SIMULATED",
            vehicle_type_mismatch=mismatch,
            invoice_id=invoice_id,
            payment_id=payment_id,
            message=out_message,
        )

    def _find_single_session(
        self,
        request: CheckOutRequest,
        operator: User,
        *,
        lock: bool = False,
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
            tx = self.repo.get_by_id(request.session_id, for_update=lock)
            if tx and (building_id is None or getattr(tx, "building_id", None) == building_id):
                sessions = [tx]
        elif request.ticket_code:
            sessions = self.repo.get_checkout_eligible_by_ticket(
                request.ticket_code.strip().upper(), building_id, for_update=lock
            )
        elif request.license_plate:
            normalized = normalize_plate(request.license_plate)
            sessions = self.repo.get_checkout_eligible_by_plate(
                normalized, building_id, for_update=lock
            )

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
        idempotency_key: str | None = None,
    ) -> CheckOutResponse:
        """
        Ghi nhận thanh toán cho phiên PAYMENT_PENDING -> PAID -> COMPLETED
        (DEMO-01, DEMO-02, IMPROVE-01, BUILD-01).
        """
        norm_method = str(payment_method).strip().upper() if payment_method else ""
        if norm_method not in ALLOWED_SESSION_PAYMENT_METHODS:
            raise AppError(
                status_code=422,
                code="INVALID_PAYMENT_METHOD",
                message=(
                    f"Phương thức thanh toán '{payment_method}' không hợp lệ. "
                    f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_SESSION_PAYMENT_METHODS))}."
                ),
            )

        paid_amount = round(float(amount), 0)
        payment_fp = fingerprint_payload(
            {
                "session_id": str(session_id),
                "payment_method": norm_method,
                "amount": paid_amount,
                "provider_ref": provider_ref,
                "override_reason": (override_reason or "").strip() or None,
            }
        )
        operator_building_id = getattr(operator, "building_id", None)
        if not isinstance(operator_building_id, UUID):
            operator_building_id = None

        validated_pay_key: str | None = None
        if idempotency_key is not None:
            validated_pay_key = validate_idempotency_key(idempotency_key)
            existing_pay_record = self.repo.get_operation_idempotency_record(
                IdempotencyOperation.RECORD_PAYMENT, validated_pay_key, operator_building_id
            )
            if existing_pay_record is not None:
                require_matching_fingerprint(existing_pay_record.request_fingerprint, payment_fp)
                replayed = self._replay_from_idempotency_record(
                    existing_pay_record.transaction_id,
                    existing_pay_record.status,
                    existing_pay_record.response_payload,
                )
                if replayed is not None:
                    return replayed

        tx = self.repo.get_by_id(session_id, for_update=True) or self.session.get(
            ParkingTransaction, session_id
        )
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

        if tx.exit_lane_id is None:
            raise AppError(
                status_code=422,
                code="EXIT_LANE_MISSING",
                message="Phiên chưa có làn ra. Vui lòng gọi lại POST /check-out trước.",
            )

        due_fee = round(float(tx.fee or 0.0), 0)
        has_reason = bool(override_reason and override_reason.strip())

        if norm_method == "OVERRIDE":
            if not has_reason:
                raise AppError(
                    status_code=422,
                    code="OVERRIDE_REASON_REQUIRED",
                    message="Vui lòng nhập lý do override thanh toán.",
                )
            if not _is_admin_operator(operator):
                raise AppError(
                    status_code=403,
                    code="OVERRIDE_FORBIDDEN",
                    message="Chỉ quản trị viên mới có quyền override miễn/giảm phí gửi xe.",
                )
        elif paid_amount != due_fee:
            if has_reason:
                if not _is_admin_operator(operator):
                    raise AppError(
                        status_code=403,
                        code="OVERRIDE_FORBIDDEN",
                        message="Chỉ quản trị viên mới có quyền override chênh lệch phí gửi xe.",
                    )
            else:
                raise AppError(
                    status_code=409,
                    code="PAYMENT_AMOUNT_MISMATCH",
                    message=(
                        f"Số tiền thanh toán ({paid_amount:,.0f}đ) không khớp với "
                        f"phí phải thu ({due_fee:,.0f}đ)."
                    ),
                    details={"expected_amount": due_fee, "received_amount": paid_amount},
                )

        try:
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
                    "payment_method": norm_method,
                    "amount": paid_amount,
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
                    "payment_method": norm_method,
                    "amount": paid_amount,
                    "provider_ref": provider_ref,
                    "override_reason": override_reason,
                },
            )
            self.session.flush()

            dummy_request = CheckOutRequest(
                session_id=tx.id,
                license_plate=tx.license_plate,
                ticket_code=tx.ticket_code,
                exit_lane_id=tx.exit_lane_id,
                override_reason=override_reason,
                payment_method=norm_method,
            )
            settled_fee = 0.0 if norm_method == "OVERRIDE" else paid_amount
            effective_pay_key = validated_pay_key or f"session-payment-{tx.id}"
            return self._complete_session(
                tx,
                dummy_request,
                operator,
                fee=settled_fee,
                key=effective_pay_key,
                checkout_fingerprint=payment_fp,
                provider_ref=provider_ref,
                idempotency_operation=IdempotencyOperation.RECORD_PAYMENT,
            )
        except Exception:
            self.session.rollback()
            raise
