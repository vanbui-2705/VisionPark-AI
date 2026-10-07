from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName
from app.modules.audit_logs.repository import list_audit_logs
from app.modules.audit_logs.schemas import PaginatedAuditResponse, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=PaginatedAuditResponse)
def list_audit(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
    actor: str | None = Query(None),
    action: str | None = Query(None),
    resource: str | None = Query(None),
    q: str | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    page: int = Query(0, ge=0),
    pageSize: int = Query(20, ge=1, le=100),
):
    items, total = list_audit_logs(db, actor=actor, action=action, resource=resource, q=q, from_time=from_time, to_time=to_time, page=page, pageSize=pageSize)
    totalPages = max(1, (total + pageSize - 1) // pageSize)
    mapped = []
    for r in items:
        mapped.append(AuditLogResponse(
            id=r.id,
            time=r.created_at,
            actor=r.user.display_name if r.user else str(r.user_id or ""),
            action=r.action,
            resource=r.entity_type,
            resource_id=r.entity_id,
            before=r.old_value,
            after=r.new_value,
            correlation_id=None,
            source=None,
        ))
    return {"items": mapped, "total": total, "page": page, "pageSize": pageSize, "totalPages": totalPages}
