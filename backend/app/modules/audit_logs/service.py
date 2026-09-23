from sqlalchemy.orm import Session
from typing import Optional, Any
from uuid import UUID
from .models import AuditLog

def log_action(
    db: Session,
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None
):
    """Hàm tiện ích để lưu vết hệ thống."""
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=old_value,
        new_value=new_value
    )
    db.add(audit_entry)