from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.middleware import correlation_id_context

from .models import AuditLog

SENSITIVE_KEY_PARTS = ("password", "secret", "token", "jwt", "hash")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
                else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def log_action(
    db: Session,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: Any | None = None,
    new_value: Any | None = None,
):
    """Hàm tiện ích để lưu vết hệ thống."""
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        correlation_id=correlation_id_context.get(),
        old_value=_redact(old_value),
        new_value=_redact(new_value),
    )
    db.add(audit_entry)
    return audit_entry
