from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName

router = APIRouter(tags=["users"])


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=6)
    role: RoleName = RoleName.OPERATOR
    active: bool = True
    email: str | None = None


class UserPatchRequest(BaseModel):
    display_name: str | None = None
    role: RoleName | None = None
    active: bool | None = None
    password: str | None = None
    email: str | None = None


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": getattr(user, "email", None),
        "role": user.role.name if user.role else RoleName.OPERATOR.value,
        "active": user.is_active,
        "is_active": user.is_active,
        "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/users")
def list_users(
    q: str | None = None,
    role: str | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))] = None,
) -> list[dict]:
    del current_user
    stmt = select(User).join(User.role).order_by(User.created_at.desc())
    if q:
        pat = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(User.username.ilike(pat), User.display_name.ilike(pat)))
    if role and role != "ALL":
        stmt = stmt.where(Role.name == role.upper())
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    users = db.scalars(stmt).all()
    return [_serialize_user(u) for u in users]


@router.get("/users/{user_id}")
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))] = None,
) -> dict:
    del current_user
    user = db.get(User, user_id)
    if not user:
        raise AppError(status_code=404, code="NOT_FOUND", message="User not found")
    return _serialize_user(user)


@router.post("/users", status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))] = None,
) -> dict:
    del current_user
    clean_username = payload.username.strip().lower()
    existing = db.scalar(select(User).where(User.username == clean_username))
    if existing:
        raise AppError(status_code=409, code="USER_EXISTS", message="Username already exists")

    role_obj = db.scalar(select(Role).where(Role.name == payload.role.value))
    if not role_obj:
        raise AppError(status_code=400, code="INVALID_ROLE", message="Role does not exist")

    user = User(
        username=clean_username,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role_id=role_obj.id,
        is_active=payload.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.patch("/users/{user_id}")
def patch_user(
    user_id: UUID,
    payload: UserPatchRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN))] = None,
) -> dict:
    del current_user
    user = db.get(User, user_id)
    if not user:
        raise AppError(status_code=404, code="NOT_FOUND", message="User not found")

    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.active is not None:
        user.is_active = payload.active
    if payload.role is not None:
        role_obj = db.scalar(select(Role).where(Role.name == payload.role.value))
        if not role_obj:
            raise AppError(status_code=400, code="INVALID_ROLE", message="Role does not exist")
        user.role_id = role_obj.id
    if payload.password:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.get("/roles")
def list_roles(
    current_user: Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.OPERATOR))] = None,
) -> list[dict]:
    del current_user
    return [
        {
            "name": "ADMIN",
            "display_name": "Quản trị viên (ADMIN)",
            "description": "Toàn quyền quản trị",
        },
        {
            "name": "OPERATOR",
            "display_name": "Nhân viên vận hành (OPERATOR)",
            "description": "Quét biển số, xác nhận và xử lý làn",
        },
        {
            "name": "ACCOUNTANT",
            "display_name": "Kế toán (ACCOUNTANT)",
            "description": "Báo cáo, giao dịch và đối soát",
        },
        {
            "name": "TECHNICIAN",
            "display_name": "Kỹ thuật viên (TECHNICIAN)",
            "description": "Giám sát hệ thống, làn và phần cứng",
        },
    ]
