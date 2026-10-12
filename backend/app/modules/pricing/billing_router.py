"""Building-scoped invoice and payment routes."""

import hashlib
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .billing import (
    CallbackPayload,
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
    apply_callback,
    create_invoice,
    create_payment,
    invoice_response,
    payment_response,
    reconcile_payments,
)
from .models import Invoice, Payment

router = APIRouter(tags=["billing"])
Db = Annotated[Session, Depends(get_db)]
BillingUser = Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN, RoleName.OPERATOR))]


def _building_id(actor: User) -> UUID:
    if actor.building_id is None:
        raise AppError(
            status_code=403, code="BUILDING_REQUIRED", message="Building assignment required."
        )
    return actor.building_id


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def post_invoice(payload: InvoiceCreate, db: Db, actor: BillingUser) -> InvoiceResponse:
    if payload.extra_free_minutes and actor.role.name != RoleName.BUILDING_ADMIN:
        raise AppError(
            status_code=403, code="FORBIDDEN", message="Free-time override requires building admin."
        )
    return invoice_response(
        create_invoice(db, building_id=_building_id(actor), actor_id=actor.id, request=payload)
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: UUID, db: Db, actor: CurrentUser) -> InvoiceResponse:
    invoice = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.building_id == _building_id(actor))
    )
    if invoice is None:
        raise AppError(status_code=404, code="INVOICE_NOT_FOUND", message="Invoice not found.")
    return invoice_response(invoice)


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def post_payment(
    payload: PaymentCreate,
    db: Db,
    actor: BillingUser,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> PaymentResponse:
    return payment_response(
        create_payment(
            db,
            building_id=_building_id(actor),
            actor_id=actor.id,
            request=payload,
            idempotency_key=idempotency_key,
        )
    )


@router.get("/payments/reconcile")
def get_reconciliation(
    db: Db,
    actor: Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))],
) -> list[dict]:
    return reconcile_payments(db, building_id=_building_id(actor))


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: UUID, db: Db, actor: CurrentUser) -> PaymentResponse:
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.building_id == _building_id(actor))
    )
    if payment is None:
        raise AppError(status_code=404, code="PAYMENT_NOT_FOUND", message="Payment not found.")
    return payment_response(payment)


@router.post("/payments/callback", response_model=PaymentResponse)
async def payment_callback(
    request: Request,
    db: Db,
    settings: Annotated[Settings, Depends(get_settings)],
    signature: Annotated[str | None, Header(alias="X-Mock-Signature")] = None,
) -> PaymentResponse:
    if settings.mock_vietqr_callback_secret is None:
        raise AppError(
            status_code=503, code="CALLBACK_DISABLED", message="Callback secret is not configured."
        )
    raw = await request.body()
    expected = hmac.new(
        settings.mock_vietqr_callback_secret.get_secret_value().encode(), raw, hashlib.sha256
    ).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected):
        raise AppError(
            status_code=401, code="INVALID_SIGNATURE", message="Invalid callback signature."
        )
    payload = CallbackPayload.model_validate_json(raw)
    return payment_response(apply_callback(db, payload))
