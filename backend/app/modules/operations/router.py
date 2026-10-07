from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.operations.models import ErrorEvent, Notification
from app.modules.operations.service import OperationsService
from app.modules.users.models import User
from app.modules.users.schemas import RoleName, UserUpdate
from app.modules.users.service import UserManagementService

router = APIRouter(tags=["account-operations"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(RoleName.ADMIN))]


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(None, max_length=254)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class Preferences(BaseModel):
    theme: Literal["light", "dark"] = "light"
    language: Literal["vi", "en"] = "vi"


class ClientErrorInput(BaseModel):
    code: str = Field(max_length=64, pattern=r"^[A-Z0-9_]+$")
    status: int = Field(ge=0, le=599)
    source: str = Field(default="frontend", max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    correlation_id: str | None = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9-]+$")


@router.patch("/auth/me")
def update_profile(payload: ProfileUpdate, user: CurrentUser, db: Db):
    return OperationsService(db).profile(
        user, UserUpdate(**payload.model_dump()).model_dump(exclude_unset=True)
    )


@router.post("/auth/change-password")
def change_password(payload: PasswordChange, user: CurrentUser, db: Db):
    OperationsService(db).change_password(user, payload.current_password, payload.new_password)
    return {"status": "changed", "sign_in_required": True}


@router.post("/auth/logout")
def logout(user: CurrentUser, db: Db):
    OperationsService(db).revoke(user, user, "LOGOUT")
    return {"status": "revoked"}


@router.post("/users/{user_id}/revoke-sessions")
def revoke_sessions(user_id: UUID, actor: Admin, db: Db):
    OperationsService(db).revoke(UserManagementService(db).get(user_id), actor)
    return {"status": "revoked"}


@router.get("/auth/preferences", response_model=Preferences)
def preferences(user: CurrentUser, db: Db):
    pref = OperationsService(db).preference(user)
    return Preferences(theme=pref.theme, language=pref.language) if pref else Preferences()


@router.put("/auth/preferences", response_model=Preferences)
def save_preferences(payload: Preferences, user: CurrentUser, db: Db):
    OperationsService(db).save_preference(user, payload.model_dump())
    return payload


@router.get("/notifications")
def notifications(
    user: CurrentUser, db: Db, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)
):
    query = select(Notification).where(Notification.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(Notification.created_at.desc(), Notification.id).offset(offset).limit(limit)
    )
    return {
        "total": total,
        "items": [
            {
                "id": str(n.id),
                "time": n.created_at,
                "title": n.title,
                "message": n.message,
                "read": n.read_at is not None,
            }
            for n in rows
        ],
    }


@router.post("/notifications/read-all")
def read_all(user: CurrentUser, db: Db):
    OperationsService(db).mark_read(user)
    return {"status": "read"}


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: UUID, user: CurrentUser, db: Db):
    OperationsService(db).mark_read(user, notification_id)
    return {"status": "read"}


@router.post("/errors", status_code=201)
def report_error(payload: ClientErrorInput, user: CurrentUser, db: Db):
    row = OperationsService(db).report_error(user, payload.model_dump())
    return {"id": str(row.id)}


@router.get("/errors")
def errors(
    actor: Admin, db: Db, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)
):
    total = db.scalar(select(func.count()).select_from(ErrorEvent))
    rows = db.scalars(
        select(ErrorEvent)
        .order_by(ErrorEvent.created_at.desc(), ErrorEvent.id)
        .offset(offset)
        .limit(limit)
    )
    return {
        "total": total,
        "items": [
            {
                "id": str(e.id),
                "time": e.created_at,
                "code": e.code,
                "status": e.status,
                "source": e.source,
                "message": e.message,
                "correlationId": e.correlation_id,
            }
            for e in rows
        ],
    }
