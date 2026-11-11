"""Shared idempotency policy and persistent checkout/payment idempotency records (BUILD-01)."""

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.errors import AppError
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.buildings.models import DEFAULT_BUILDING_ID, BuildingOwnedMixin


class IdempotencyOperation(StrEnum):
    CHECKOUT = "CHECKOUT"
    RECORD_PAYMENT = "RECORD_PAYMENT"


class IdempotencyRecord(BuildingOwnedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persistent idempotency ledger for checkout and session payment operations (BUILD-01)."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "building_id",
            "operation",
            "key",
            name="uq_idempotency_records_building_op_key",
        ),
        CheckConstraint(
            "length(key) BETWEEN 1 AND 255",
            name="ck_idempotency_records_key",
        ),
        CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_idempotency_records_fingerprint",
        ),
        CheckConstraint(
            "operation IN ('CHECKOUT', 'RECORD_PAYMENT')",
            name="ck_idempotency_records_operation",
        ),
    )

    key: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parking_transactions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def validate_idempotency_key(key: str | None) -> str:
    if key is None or not key.strip():
        raise AppError(
            status_code=422,
            code="IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key header is required.",
        )
    normalized = key.strip()
    if len(normalized) > 255:
        raise AppError(
            status_code=422,
            code="INVALID_IDEMPOTENCY_KEY",
            message="Idempotency-Key must contain at most 255 characters.",
        )
    return normalized


def resolve_idempotency_key(header_key: str | None, body_key: str | None) -> str:
    """Validate and reconcile header and body Idempotency-Key values."""
    if header_key is not None and body_key is not None and header_key.strip() != body_key.strip():
        raise AppError(
            status_code=422,
            code="IDEMPOTENCY_KEY_MISMATCH",
            message="Idempotency-Key header and request body idempotency_key must match.",
        )
    raw_key = header_key if header_key is not None else body_key
    return validate_idempotency_key(raw_key)


def fingerprint_payload(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(
        payload, default=str, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def require_matching_fingerprint(stored: str, requested: str) -> None:
    if stored != requested:
        raise AppError(
            status_code=409,
            code="IDEMPOTENCY_KEY_REUSED",
            message="Idempotency-Key was already used with a different payload.",
        )


def get_idempotency_record(
    session: Session,
    *,
    operation: str,
    key: str,
    building_id: UUID | None = None,
) -> IdempotencyRecord | None:
    """Look up an existing IdempotencyRecord and verify payload fingerprint if needed."""
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.operation == operation,
        IdempotencyRecord.key == key,
    )
    effective_building = building_id or session.info.get("building_id")
    if effective_building is not None:
        stmt = stmt.where(IdempotencyRecord.building_id == effective_building)
    return session.scalar(stmt)


def upsert_idempotency_record(
    session: Session,
    *,
    building_id: UUID | None,
    operation: str,
    key: str,
    request_fingerprint: str,
    transaction_id: UUID | None,
    status: str,
    response_payload: dict | None = None,
) -> IdempotencyRecord:
    """Create or update an IdempotencyRecord in the caller's current transaction."""
    effective_building = building_id or session.info.get("building_id") or DEFAULT_BUILDING_ID
    existing = get_idempotency_record(
        session,
        operation=operation,
        key=key,
        building_id=effective_building,
    )
    if existing is not None:
        require_matching_fingerprint(existing.request_fingerprint, request_fingerprint)
        existing.transaction_id = transaction_id
        existing.status = status
        if response_payload is not None:
            existing.response_payload = response_payload
        session.flush()
        return existing

    record = IdempotencyRecord(
        building_id=effective_building,
        key=key,
        operation=operation,
        request_fingerprint=request_fingerprint,
        transaction_id=transaction_id,
        status=status,
        response_payload=response_payload,
    )
    session.add(record)
    session.flush()
    return record


def encode_checkout_idempotency_tag(key: str, fingerprint: str) -> str:
    """Format checkout idempotency marker with request fingerprint (legacy/fallback helper)."""
    return f"[CHECKOUT_KEY:{key}][CHECKOUT_FP:{key}:{fingerprint}]"


def extract_checkout_fingerprint(notes: str | None, key: str) -> str | None:
    """Extract stored request fingerprint for a checkout idempotency key if present."""
    if not notes:
        return None
    prefix = f"[CHECKOUT_FP:{key}:"
    start = notes.find(prefix)
    if start == -1:
        return None
    fp_start = start + len(prefix)
    fp_end = notes.find("]", fp_start)
    if fp_end == -1:
        return None
    return notes[fp_start:fp_end]


def verify_checkout_idempotency(notes: str | None, key: str, requested_fingerprint: str) -> None:
    """Verify that a replayed checkout idempotency key matches its original request payload."""
    stored = extract_checkout_fingerprint(notes, key)
    if stored is not None:
        require_matching_fingerprint(stored, requested_fingerprint)
