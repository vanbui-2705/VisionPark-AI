"""Shared idempotency policy; persistence uses the caller's request-scoped session."""

import hashlib
import json
from collections.abc import Mapping

from app.core.errors import AppError


def validate_idempotency_key(key: str | None) -> str:
    if key is None or not key.strip():
        raise AppError(
            status_code=422,
            code="IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key header is required.",
        )
    if len(key) > 255:
        raise AppError(
            status_code=422,
            code="INVALID_IDEMPOTENCY_KEY",
            message="Idempotency-Key must contain at most 255 characters.",
        )
    return key


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


def encode_checkout_idempotency_tag(key: str, fingerprint: str) -> str:
    """Format checkout idempotency marker with request fingerprint (BUILD-01)."""
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
