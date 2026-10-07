from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.modules.audit_logs.service import log_action
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    ManagedUserPublic,
    RoleName,
    UserCreate,
    UserPublic,
    UserUpdate,
)


def to_public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=RoleName(user.role.name),
        is_active=user.is_active,
        email=user.email,
        last_login_at=user.last_login_at,
    )


def to_managed_user(user: User) -> ManagedUserPublic:
    return ManagedUserPublic(**to_public_user(user).model_dump(), created_at=user.created_at)


class UserManagementService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = UserRepository(session)

    def get(self, user_id: UUID) -> User:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="User not found.")
        return user

    def create(self, payload: UserCreate, actor: User | None) -> ManagedUserPublic:
        if self.repo.get_by_username(payload.username) or (
            payload.email and self.repo.get_by_email(payload.email)
        ):
            raise AppError(
                status_code=409, code="DUPLICATE_USER", message="Username or email already exists."
            )
        role = self.repo.get_role(payload.role.value)
        if role is None:
            raise AppError(status_code=422, code="INVALID_ROLE", message="Role is not provisioned.")
        user = User(
            username=payload.username,
            display_name=payload.display_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=role,
            is_active=payload.active,
        )
        self.session.add(user)
        self._save(user, actor, "CREATE_USER", None)
        return to_managed_user(user)

    def update(self, user_id: UUID, payload: UserUpdate, actor: User) -> ManagedUserPublic:
        user = self.get(user_id)
        values = payload.model_dump(exclude_unset=True)
        if user.id == actor.id and (
            values.get("active") is False or ("role" in values and values["role"] != RoleName.ADMIN)
        ):
            raise AppError(
                status_code=409,
                code="SELF_ACCESS_CHANGE",
                message="You cannot disable or demote your own administrator account.",
            )
        if values.get("email"):
            existing = self.repo.get_by_email(values["email"])
            if existing and existing.id != user.id:
                raise AppError(
                    status_code=409, code="DUPLICATE_USER", message="Email already exists."
                )
        if any(key in values for key in ("password", "active", "role")):
            user.token_version += 1
        before = to_managed_user(user).model_dump(mode="json")
        if "role" in values:
            role = self.repo.get_role(values.pop("role").value)
            if role is None:
                raise AppError(
                    status_code=422, code="INVALID_ROLE", message="Role is not provisioned."
                )
            user.role = role
        if "password" in values:
            user.password_hash = hash_password(values.pop("password"))
        if "active" in values:
            user.is_active = values.pop("active")
        for name, value in values.items():
            setattr(user, name, value)
        self._save(user, actor, "UPDATE_USER", before)
        return to_managed_user(user)

    def _save(self, user: User, actor: User | None, action: str, before):
        try:
            self.session.flush()
            log_action(
                self.session,
                actor.id if actor else None,
                action,
                "User",
                str(user.id),
                before,
                to_managed_user(user).model_dump(mode="json"),
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                status_code=409, code="DUPLICATE_USER", message="Username or email already exists."
            ) from exc
        self.session.refresh(user)
