from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.modules.audit_logs.models import AuditLog
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.schemas import AuditLogResponse
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    actor: str | None = None,
    action: str | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    limit: int = Query(100, ge=1, le=200),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> list[AuditLogResponse]:
    del current_user
    stmt = (
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if actor:
        stmt = stmt.join(AuditLog.user).where(User.username.ilike(f"%{actor}%"))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if from_time:
        stmt = stmt.where(AuditLog.created_at >= from_time)
    if to_time:
        stmt = stmt.where(AuditLog.created_at <= to_time)
    rows = db.scalars(stmt).unique().all()
    return [
        AuditLogResponse(
            id=row.id,
            time=row.created_at,
            actor=row.user.display_name if row.user else None,
            action=row.action,
            resource=row.entity_type,
            resource_id=row.entity_id,
            source=(row.new_value or {}).get("source") if isinstance(row.new_value, dict) else None,
            before=row.old_value,
            after=row.new_value,
        )
        for row in rows
    ]
