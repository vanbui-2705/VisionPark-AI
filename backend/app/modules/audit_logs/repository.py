from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload

from app.modules.audit_logs.models import AuditLog
from app.modules.users.models import User


def list_audit_logs(
    db: Session,
    *,
    actor: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    q: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    page: int = 0,
    pageSize: int = 20,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.created_at.desc())
    count_q = select(func.count()).select_from(AuditLog)

    # join user for actor filter
    if actor:
        # actor is display_name / username substring
        query = query.join(User, AuditLog.user_id == User.id, isouter=True).where(or_(User.display_name.ilike(f"%{actor}%"), User.username.ilike(f"%{actor}%")))
        count_q = count_q.join(User, AuditLog.user_id == User.id, isouter=True).where(or_(User.display_name.ilike(f"%{actor}%"), User.username.ilike(f"%{actor}%")))
    if action:
        query = query.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if resource:
        query = query.where(AuditLog.entity_type == resource)
        count_q = count_q.where(AuditLog.entity_type == resource)
    if q:
        like = f"%{q}%"
        cond = or_(AuditLog.action.ilike(like), AuditLog.entity_type.ilike(like), AuditLog.entity_id.ilike(like))
        query = query.where(cond)
        count_q = count_q.where(cond)
    if from_time:
        query = query.where(AuditLog.created_at >= from_time)
        count_q = count_q.where(AuditLog.created_at >= from_time)
    if to_time:
        query = query.where(AuditLog.created_at <= to_time)
        count_q = count_q.where(AuditLog.created_at <= to_time)

    total = db.scalar(count_q) or 0
    items = list(db.scalars(query.offset(page * pageSize).limit(pageSize)).all())
    return items, total
