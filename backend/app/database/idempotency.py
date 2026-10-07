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
