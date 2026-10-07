from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func as _func
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.audit_logs.models import AuditLog
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.schemas import AuditLogResponse, PaginatedAuditLogs
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/", response_model=dict | PaginatedAuditLogs | list[AuditLogResponse])
def list_audit_logs(
    request: Request,
    actor: str | None = None,
    actor_id: UUID | None = None,
    action: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    q: str | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    page: int | None = Query(None, ge=0),
    pageSize: int | None = Query(None, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=200),
    skip: int | None = Query(None, ge=0),
    offset: int = Query(0, ge=0),
    paginated: bool = False,
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
):
    del current_user
    is_paginated = (
        paginated
        or ("page" in request.query_params)
        or ("pageSize" in request.query_params)
        or (request.query_params.get("format") == "paginated")
    )
    eff_page_size = pageSize if pageSize is not None else (limit if limit is not None else 20)
    eff_skip = (
        (page * eff_page_size) if page is not None else (skip if skip is not None else offset)
    )
    eff_page = page if page is not None else (eff_skip // max(1, eff_page_size))

    if eff_page < 0 or eff_page_size < 1 or eff_page_size > 100:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="Invalid page/pageSize")

    stmt = select(AuditLog).options(joinedload(AuditLog.user))
    count_stmt = select(_func.count()).select_from(AuditLog)

    if actor or q:
        stmt = stmt.outerjoin(AuditLog.user)
        count_stmt = count_stmt.outerjoin(AuditLog.user)

    if actor_id:
        stmt = stmt.where(AuditLog.user_id == actor_id)
        count_stmt = count_stmt.where(AuditLog.user_id == actor_id)
    if resource_id:
        stmt = stmt.where(AuditLog.entity_id == resource_id)
        count_stmt = count_stmt.where(AuditLog.entity_id == resource_id)

    if actor:
        actor_pat = f"%{actor}%"
        actor_cond = or_(User.username.ilike(actor_pat), User.display_name.ilike(actor_pat))
        stmt = stmt.where(actor_cond)
        count_stmt = count_stmt.where(actor_cond)

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)

    if resource:
        stmt = stmt.where(AuditLog.entity_type == resource)
        count_stmt = count_stmt.where(AuditLog.entity_type == resource)

    if q:
        q_pat = f"%{q}%"
        q_cond = or_(
            AuditLog.action.ilike(q_pat),
            AuditLog.entity_type.ilike(q_pat),
            AuditLog.entity_id.ilike(q_pat),
            User.username.ilike(q_pat),
            User.display_name.ilike(q_pat),
        )
        stmt = stmt.where(q_cond)
        count_stmt = count_stmt.where(q_cond)

    if from_time:
        stmt = stmt.where(AuditLog.created_at >= from_time)
        count_stmt = count_stmt.where(AuditLog.created_at >= from_time)

    if to_time:
        stmt = stmt.where(AuditLog.created_at <= to_time)
        count_stmt = count_stmt.where(AuditLog.created_at <= to_time)

    total = db.scalar(count_stmt) or 0
    total_pages = max(1, (total + eff_page_size - 1) // eff_page_size)

    rows = (
        db.scalars(
            stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(eff_skip)
            .limit(eff_page_size)
        )
        .unique()
        .all()
    )

    items = [
        AuditLogResponse(
            id=row.id,
            time=row.created_at,
            actor=row.user.display_name if row.user else None,
            action=row.action,
            resource=row.entity_type,
            resource_id=row.entity_id,
            source=(
                (row.new_value or {}).get("source") if isinstance(row.new_value, dict) else None
            ),
            before=row.old_value,
            after=row.new_value,
        )
        for row in rows
    ]

    if is_paginated:
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "data": items,
            "total": total,
            "page": eff_page,
            "pageSize": eff_page_size,
            "totalPages": total_pages,
            "limit": eff_page_size,
            "offset": eff_skip,
        }
    return items
