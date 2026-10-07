from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import AuditLog


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
        old_value=old_value,
        new_value=new_value,
    )
    db.add(audit_entry)
