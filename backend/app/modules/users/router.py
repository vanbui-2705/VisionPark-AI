from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import Role, User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import ManagedUserPublic, RoleName, UserCreate, UserUpdate
from app.modules.users.service import UserManagementService, to_managed_user

router = APIRouter(tags=["users"])
Admin = Annotated[User, Depends(require_roles(RoleName.ADMIN))]
Db = Annotated[Session, Depends(get_db)]


@router.get("/users", response_model=list[ManagedUserPublic])
def list_users(
    db: Db,
    actor: Admin,
    q: str | None = None,
    role: RoleName | None = None,
    active: bool | None = None,
):
    return [to_managed_user(user) for user in UserRepository(db).list(q, role, active)]


@router.get("/users/{user_id}", response_model=ManagedUserPublic)
def read_user(user_id: UUID, db: Db, actor: Admin):
    return to_managed_user(UserManagementService(db).get(user_id))


@router.post("/users", response_model=ManagedUserPublic, status_code=201)
def create_user(payload: UserCreate, db: Db, actor: Admin):
    return UserManagementService(db).create(payload, actor)


@router.patch("/users/{user_id}", response_model=ManagedUserPublic)
def update_user(user_id: UUID, payload: UserUpdate, db: Db, actor: Admin):
    return UserManagementService(db).update(user_id, payload, actor)


@router.get("/roles")
def list_roles(db: Db, actor: Admin):
    return [
        {"name": role.name, "display_name": role.name, "description": ""}
        for role in db.scalars(select(Role).order_by(Role.name))
    ]
