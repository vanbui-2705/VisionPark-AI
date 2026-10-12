"""Invoice and mock payment lifecycle for a trusted building context."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit_logs.service import log_action
from app.modules.checkin.models import ParkingTransaction, TransactionStatus

from .domain import FeeLine, PriceSnapshot, calculate_fee
from .models import GuestInvite, Invoice, Payment


class PaymentMethod(StrEnum):
    CASH = "CASH"
    VIETQR_MOCK = "VIETQR_MOCK"


class ProviderStatus(StrEnum):
    PAID = "PAID"
    FAILED = "FAILED"
    PROCESSING = "PROCESSING"
    REFUNDED = "REFUNDED"


class InvoiceCreate(BaseModel):
    transaction_id: UUID
    check_out: datetime
    lost_ticket: bool = False
    overtime: bool = False
    extra_free_minutes: int = Field(default=0, ge=0)
    guest_invite_code: str | None = None

    @model_validator(mode="after")
    def require_timezone(self) -> "InvoiceCreate":
        if self.check_out.tzinfo is None:
            raise ValueError("check_out must include a timezone")
        return self


class InvoiceResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    price_version_id: UUID
    status: str
    total_vnd: int
    currency: str = "VND"
    lines: list[FeeLine]


class PaymentCreate(BaseModel):
    invoice_id: UUID
    method: PaymentMethod


class PaymentResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    provider_ref: str | None
    method: PaymentMethod
    status: str
    amount_vnd: int
    currency: str = "VND"
    mock_qr_payload: str | None = None


class CallbackPayload(BaseModel):
    provider_ref: str = Field(min_length=1, max_length=120)
    amount_vnd: int = Field(ge=0)
    status: ProviderStatus


def invoice_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        transaction_id=invoice.transaction_id,
        price_version_id=invoice.price_version_id,
        status=invoice.status,
        total_vnd=invoice.total_vnd,
        lines=[FeeLine.model_validate(line) for line in invoice.lines],
    )


def payment_response(payment: Payment) -> PaymentResponse:
    qr = None
    if payment.method == PaymentMethod.VIETQR_MOCK:
        qr = f"MOCK-VIETQR:{payment.provider_ref}:{payment.amount_vnd}"
    return PaymentResponse(
        id=payment.id,
        invoice_id=payment.invoice_id,
        provider_ref=payment.provider_ref,
        method=payment.method,
        status=payment.status,
        amount_vnd=payment.amount_vnd,
        mock_qr_payload=qr,
    )


def create_invoice(
    db: Session, *, building_id: UUID, actor_id: UUID, request: InvoiceCreate
) -> Invoice:
    transaction = db.scalar(
        select(ParkingTransaction)
        .where(
            ParkingTransaction.id == request.transaction_id,
            ParkingTransaction.building_id == building_id,
        )
        .with_for_update()
    )
    if transaction is None:
        raise AppError(
            status_code=404, code="TRANSACTION_NOT_FOUND", message="Transaction not found."
        )
    existing = db.scalar(select(Invoice).where(Invoice.transaction_id == transaction.id))
    if existing is not None:
        existing_invite = (
            db.get(GuestInvite, existing.guest_invite_id) if existing.guest_invite_id else None
        )
        existing_checkout = existing.check_out_time
        if existing_checkout.tzinfo is None:
            existing_checkout = existing_checkout.replace(tzinfo=UTC)
        if (
            existing_checkout.astimezone(UTC) != request.check_out.astimezone(UTC)
            or existing.lost_ticket != request.lost_ticket
            or existing.overtime != request.overtime
            or existing.extra_free_minutes
            != request.extra_free_minutes + (existing_invite.free_minutes if existing_invite else 0)
            or (existing_invite.code if existing_invite else None) != request.guest_invite_code
        ):
            raise AppError(
                status_code=409, code="INVOICE_EXISTS", message="Invoice already exists."
            )
        return existing
    if transaction.status != TransactionStatus.PARKED:
        raise AppError(status_code=409, code="NOT_PARKED", message="Transaction is not parked.")
    if not transaction.price_snapshot:
        raise AppError(status_code=409, code="PRICE_MISSING", message="No check-in price snapshot.")
    snapshot = PriceSnapshot.model_validate(transaction.price_snapshot)
    invite = None
    if request.guest_invite_code:
        invite = db.scalar(
            select(GuestInvite)
            .where(
                GuestInvite.building_id == building_id,
                GuestInvite.code == request.guest_invite_code,
            )
            .with_for_update()
        )
        if invite is None or invite.redeemed_at is not None:
            raise AppError(
                status_code=409, code="INVITE_UNAVAILABLE", message="Guest invite is unavailable."
            )
        valid_from = invite.valid_from.replace(tzinfo=invite.valid_from.tzinfo or UTC)
        valid_until = invite.valid_until.replace(tzinfo=invite.valid_until.tzinfo or UTC)
        if not valid_from <= request.check_out <= valid_until:
            raise AppError(
                status_code=409,
                code="INVITE_EXPIRED",
                message="Guest invite is outside its validity window.",
            )
    check_in = transaction.check_in_time
    if check_in.tzinfo is None:
        check_in = check_in.replace(tzinfo=UTC)
    if request.check_out <= check_in:
        raise AppError(
            status_code=422, code="INVALID_CHECKOUT", message="Check-out must follow check-in."
        )
    fee = calculate_fee(
        check_in=check_in,
        check_out=request.check_out,
        snapshot=snapshot,
        lost_ticket=request.lost_ticket,
        overtime=request.overtime,
        extra_free_minutes=request.extra_free_minutes + (invite.free_minutes if invite else 0),
    )
    invoice = Invoice(
        building_id=building_id,
        transaction_id=transaction.id,
        price_version_id=snapshot.version_id,
        status="OPEN",
        check_out_time=request.check_out,
        lost_ticket=request.lost_ticket,
        overtime=request.overtime,
        extra_free_minutes=request.extra_free_minutes + (invite.free_minutes if invite else 0),
        guest_invite_id=invite.id if invite else None,
        total_vnd=fee.total,
        lines=[line.model_dump(mode="json") for line in fee.lines],
    )
    db.add(invoice)
    if invite is not None:
        invite.redeemed_at = datetime.now(UTC)
    db.flush()
    log_action(
        db,
        actor_id,
        "CREATE_INVOICE",
        "Invoice",
        str(invoice.id),
        new_value={"transaction_id": str(transaction.id), "total_vnd": fee.total},
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def create_payment(
    db: Session,
    *,
    building_id: UUID,
    actor_id: UUID,
    request: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    invoice = db.scalar(
        select(Invoice)
        .where(Invoice.id == request.invoice_id, Invoice.building_id == building_id)
        .with_for_update()
    )
    if invoice is None:
        raise AppError(status_code=404, code="INVOICE_NOT_FOUND", message="Invoice not found.")
    existing = db.scalar(
        select(Payment).where(
            Payment.invoice_id == invoice.id,
            Payment.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.method != request.method:
            raise AppError(status_code=409, code="IDEMPOTENCY_CONFLICT", message="Payment differs.")
        return existing
    if invoice.status == "PAID":
        raise AppError(status_code=409, code="INVOICE_PAID", message="Invoice is already paid.")
    pending = db.scalar(
        select(Payment.id).where(
            Payment.invoice_id == invoice.id,
            Payment.status.in_(("PENDING", "PROCESSING")),
        )
    )
    if pending is not None:
        raise AppError(
            status_code=409,
            code="PAYMENT_PENDING",
            message="An active payment already exists for this invoice.",
        )
    payment = Payment(
        building_id=building_id,
        invoice_id=invoice.id,
        provider_ref=uuid4().hex if request.method == PaymentMethod.VIETQR_MOCK else None,
        idempotency_key=idempotency_key,
        method=request.method,
        status="PAID" if request.method == PaymentMethod.CASH else "PENDING",
        amount_vnd=invoice.total_vnd,
        confirmed_at=datetime.now(UTC) if request.method == PaymentMethod.CASH else None,
    )
    db.add(payment)
    if request.method == PaymentMethod.CASH:
        invoice.status = "PAID"
    try:
        db.flush()
        log_action(
            db,
            actor_id,
            "CREATE_PAYMENT",
            "Payment",
            str(payment.id),
            new_value={
                "invoice_id": str(invoice.id),
                "method": request.method,
                "status": payment.status,
                "amount_vnd": payment.amount_vnd,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        replay = db.scalar(
            select(Payment).where(
                Payment.invoice_id == request.invoice_id,
                Payment.idempotency_key == idempotency_key,
            )
        )
        if replay is not None and replay.method == request.method:
            return replay
        raise AppError(
            status_code=409, code="PAYMENT_CONFLICT", message="Payment conflict."
        ) from exc
    db.refresh(payment)
    return payment


def apply_callback(db: Session, payload: CallbackPayload) -> Payment:
    payment = db.scalar(
        select(Payment).where(Payment.provider_ref == payload.provider_ref).with_for_update()
    )
    if payment is None:
        raise AppError(status_code=404, code="PAYMENT_NOT_FOUND", message="Payment not found.")
    if payment.method != PaymentMethod.VIETQR_MOCK:
        raise AppError(status_code=409, code="INVALID_PAYMENT_METHOD", message="Invalid method.")
    if (
        payment.provider_status == payload.status
        and payment.provider_amount_vnd == payload.amount_vnd
    ):
        return payment
    if payment.status == "PAID" and payload.status == ProviderStatus.REFUNDED:
        if payload.amount_vnd != payment.amount_vnd:
            raise AppError(
                status_code=409, code="REFUND_AMOUNT_MISMATCH", message="Refund amount differs."
            )
        invoice = db.scalar(
            select(Invoice).where(Invoice.id == payment.invoice_id).with_for_update()
        )
        payment.provider_status = payload.status
        payment.provider_amount_vnd = payload.amount_vnd
        payment.status = "REFUNDED"
        invoice.status = "REFUNDED"
        log_action(
            db,
            None,
            "PAYMENT_REFUNDED",
            "Payment",
            str(payment.id),
            new_value={"provider_ref": payment.provider_ref, "amount_vnd": payload.amount_vnd},
        )
        db.commit()
        db.refresh(payment)
        return payment
    if payment.status in {"PAID", "REFUNDED"}:
        raise AppError(status_code=409, code="PAYMENT_FINAL", message="Payment is final.")
    invoice = db.scalar(select(Invoice).where(Invoice.id == payment.invoice_id).with_for_update())
    payment.provider_status = payload.status
    payment.provider_amount_vnd = payload.amount_vnd
    if payload.amount_vnd != payment.amount_vnd or payload.amount_vnd != invoice.total_vnd:
        payment.status = "FAILED"
    else:
        payment.status = payload.status.value
        if payload.status == ProviderStatus.PAID:
            payment.confirmed_at = datetime.now(UTC)
            invoice.status = "PAID"
    log_action(
        db,
        None,
        "PAYMENT_CALLBACK",
        "Payment",
        str(payment.id),
        new_value={
            "provider_ref": payment.provider_ref,
            "provider_status": payment.provider_status,
            "provider_amount_vnd": payment.provider_amount_vnd,
            "status": payment.status,
        },
    )
    db.commit()
    db.refresh(payment)
    return payment


def reconcile_payments(db: Session, *, building_id: UUID) -> list[dict]:
    rows = db.execute(
        select(Payment, Invoice)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(Payment.building_id == building_id, Payment.method == PaymentMethod.VIETQR_MOCK)
    )
    mismatches = []
    for payment, invoice in rows:
        reasons = []
        if (
            payment.provider_amount_vnd is not None
            and payment.provider_amount_vnd != invoice.total_vnd
        ):
            reasons.append("AMOUNT_MISMATCH")
        if payment.provider_status == ProviderStatus.PAID and payment.status != "PAID":
            reasons.append("STATUS_MISMATCH")
        if payment.status == "PAID" and invoice.status != "PAID":
            reasons.append("INVOICE_STATUS_MISMATCH")
        if reasons:
            mismatches.append(
                {"payment_id": str(payment.id), "invoice_id": str(invoice.id), "reasons": reasons}
            )
    return mismatches
