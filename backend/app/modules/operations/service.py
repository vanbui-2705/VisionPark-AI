from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.modules.audit_logs.service import log_action
from app.modules.operations.models import ErrorEvent, Notification, UserPreference
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate
from app.modules.users.service import UserManagementService


class OperationsService:
    def __init__(self, db: Session):
        self.db = db

    def profile(self, user, payload):
        # Personal updates cannot change role, active state or password.
        return UserManagementService(self.db).update(user.id, UserUpdate(**payload), user)

    def change_password(self, user, current_password: str, new_password: str):
        if not verify_password(current_password, user.password_hash):
            raise AppError(
                status_code=422, code="INVALID_PASSWORD", message="Current password is incorrect."
            )
        user.password_hash = hash_password(new_password)
        self.revoke(user, user, "CHANGE_PASSWORD")

    def revoke(self, user, actor, action="REVOKE_SESSIONS"):
        self.db.execute(
            update(User).where(User.id == user.id).values(token_version=User.token_version + 1)
        )
        log_action(self.db, actor.id, action, "User", str(user.id))
        self.db.add(
            Notification(
                user_id=user.id,
                title="Account security",
                message="Your sessions were revoked. Please sign in again.",
                event_key=f"security-{uuid4()}",
            )
        )
        self.db.commit()

    def mark_read(self, user, notification_id=None):
        query = select(Notification).where(Notification.user_id == user.id)
        if notification_id is not None:
            query = query.where(Notification.id == notification_id)
        rows = list(self.db.scalars(query))
        if notification_id is not None and not rows:
            raise AppError(status_code=404, code="NOT_FOUND", message="Notification not found.")
        for row in rows:
            if row.read_at is None:
                row.read_at = datetime.now(UTC)
        self.db.commit()

    def preference(self, user):
        return self.db.get(UserPreference, user.id)

    def save_preference(self, user, values):
        pref = self.preference(user)
        if pref is None:
            pref = UserPreference(user_id=user.id)
            self.db.add(pref)
        for key, value in values.items():
            setattr(pref, key, value)
        self.db.commit()
        return pref

    def report_error(self, user, values):
        # Serialize per-user ingestion so simultaneous requests cannot bypass the limit.
        self.db.scalar(select(User).where(User.id == user.id).with_for_update(of=User))
        correlation = values.get("correlation_id")
        if correlation:
            existing = self.db.scalar(
                select(ErrorEvent).where(
                    ErrorEvent.user_id == user.id,
                    ErrorEvent.correlation_id == correlation,
                    ErrorEvent.code == values["code"],
                    ErrorEvent.source == values["source"],
                )
            )
            if existing:
                return existing
        cutoff = datetime.now(UTC) - timedelta(minutes=1)
        count = self.db.scalar(
            select(func.count())
            .select_from(ErrorEvent)
            .where(ErrorEvent.user_id == user.id, ErrorEvent.created_at >= cutoff)
        )
        if count >= 10:
            raise AppError(status_code=429, code="RATE_LIMIT", message="Too many error reports.")
        # Client strings are untrusted: preserve identifiers, never raw error messages/payloads.
        code = values["code"]
        event = ErrorEvent(
            user_id=user.id,
            code=code,
            status=values["status"],
            source=values["source"],
            correlation_id=values.get("correlation_id"),
            message=f"Request failed ({code}).",
        )
        self.db.add(event)
        self.db.add(
            Notification(
                user_id=user.id,
                title="Request error",
                message=f"An operation failed ({code}).",
                event_key=f"error-{uuid4()}",
            )
        )
        self.db.commit()
        return event
