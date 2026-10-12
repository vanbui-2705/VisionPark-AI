from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.modules.audit_logs.service import log_action
from app.modules.buildings.models import DEFAULT_BUILDING_ID, Building, UserBuilding
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
        must_change_password=user.must_change_password,
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
        self._authorize_role(actor, payload.role)
        scope = self.session.info.get("building_id")
        if scope is not None and payload.building_id is not None:
            raise AppError(
                status_code=403,
                code="BUILDING_ACCESS_DENIED",
                message="Staff building is resolved from your account.",
            )
        building_id = scope or payload.building_id or DEFAULT_BUILDING_ID
        building = self.session.get(Building, building_id)
        if building is None or not building.is_active:
            raise AppError(status_code=404, code="NOT_FOUND", message="Active building not found.")
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
            must_change_password=payload.role == RoleName.BUILDING_ADMIN,
        )
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                status_code=409, code="DUPLICATE_USER", message="Username or email already exists."
            ) from exc
        self.session.add(
            UserBuilding(
                user_id=user.id,
                building_id=building_id,
            )
        )
        self._save(user, actor, "CREATE_USER", None)
        return to_managed_user(user)

    def update(self, user_id: UUID, payload: UserUpdate, actor: User) -> ManagedUserPublic:
        user = self.get(user_id)
        values = payload.model_dump(exclude_unset=True)
        access_change = any(key in values for key in ("role", "active", "password"))
        if (
            actor.role.name == RoleName.BUILDING_ADMIN
            and user.id != actor.id
            and user.role.name not in {RoleName.OPERATOR, RoleName.ACCOUNTANT}
        ):
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Building administrators manage staff accounts only.",
            )
        if actor.role.name == RoleName.BUILDING_ADMIN and access_change:
            if user.role.name not in {RoleName.OPERATOR, RoleName.ACCOUNTANT}:
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN",
                    message="Building administrators manage staff accounts only.",
                )
            if "role" in values:
                self._authorize_role(actor, values["role"])
        if user.id == actor.id and (
            values.get("active") is False
            or ("role" in values and values["role"].value != actor.role.name)
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
            user.must_change_password = True
        if "active" in values:
            user.is_active = values.pop("active")
        for name, value in values.items():
            setattr(user, name, value)
        self._save(user, actor, "UPDATE_USER", before)
        return to_managed_user(user)

    def _save(self, user: User, actor: User | None, action: str, before):
        try:
            self.session.flush()
            membership = self.session.scalar(
                select(UserBuilding).where(UserBuilding.user_id == user.id)
            )
            entry = log_action(
                self.session,
                actor.id if actor else None,
                action,
                "User",
                str(user.id),
                before,
                to_managed_user(user).model_dump(mode="json"),
            )
            if membership is not None:
                entry.building_id = membership.building_id
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                status_code=409, code="DUPLICATE_USER", message="Username or email already exists."
            ) from exc
        self.session.refresh(user)

    @staticmethod
    def _authorize_role(actor: User | None, role: RoleName):
        if actor is None or (
            actor.role.name == RoleName.BUILDING_ADMIN
            and role not in {RoleName.OPERATOR, RoleName.ACCOUNTANT}
        ):
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Only system administrators provision management accounts.",
            )
