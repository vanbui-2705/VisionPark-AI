from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.modules.audit_logs.models import AuditLog
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.schemas import AuditLogResponse, PaginatedAuditLogs
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/", response_model=dict | PaginatedAuditLogs | list[AuditLogResponse])
def list_audit_logs(
    actor: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    q: str | None = None,
    actor_id: UUID | None = None,
    resource_id: str | None = None,
    offset: int = Query(0, ge=0),
    paginated: bool = False,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    limit: int = Query(100, ge=1, le=200),
    page: int = Query(0, ge=0),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
):
    del current_user
    stmt = (
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if actor_id:
        stmt = stmt.where(AuditLog.user_id == actor_id)
    if resource_id:
        stmt = stmt.where(AuditLog.entity_id == resource_id)
    if resource:
        stmt = stmt.where(AuditLog.entity_type == resource)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                AuditLog.action.ilike(pattern),
                AuditLog.entity_type.ilike(pattern),
                AuditLog.entity_id.ilike(pattern),
            )
        )
    if actor:
        stmt = stmt.join(AuditLog.user).where(User.username.ilike(f"%{actor}%"))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if from_time:
        stmt = stmt.where(AuditLog.created_at >= from_time)
    if to_time:
        stmt = stmt.where(AuditLog.created_at <= to_time)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    
    # support both page/limit and offset/limit
    actual_offset = offset if offset > 0 else (page * limit)
    stmt = stmt.offset(actual_offset).limit(limit)
    rows = db.scalars(stmt).unique().all()

    items = [
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

    # Support our phase 3 pagination (if page was provided implicitly or explicitly)
    # but also support main's paginated dict if requested
    if paginated:
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
            "limit": limit,
            "offset": actual_offset,
            # include our fields too just in case
            "data": items,
            "page": page,
        }
        
    return PaginatedAuditLogs(
        data=items,
        total=total,
        page=page,
        limit=limit,
    )
