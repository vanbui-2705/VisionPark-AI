import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.audit_logs.models import AuditLog
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.buildings.models import Building, ParkingLot
from app.modules.buildings.schemas import (
    BuildingAdminCreate,
    BuildingCreate,
    BuildingPublic,
    BuildingState,
)
from app.modules.lot_settings.schemas import default_settings
from app.modules.users.models import User
from app.modules.users.schemas import RoleName, UserCreate
from app.modules.users.service import UserManagementService

router = APIRouter(prefix="/buildings", tags=["buildings"])
Db = Annotated[Session, Depends(get_db)]
SystemAdmin = Annotated[User, Depends(require_roles(RoleName.SYSTEM_ADMIN))]


@router.get("", response_model=list[BuildingPublic])
def list_buildings(db: Db, actor: CurrentUser):
    return db.scalars(select(Building).order_by(Building.code)).all()


@router.post("", response_model=BuildingPublic, status_code=201)
def create_building(payload: BuildingCreate, db: Db, actor: SystemAdmin):
    row = Building(**payload.model_dump())
    db.add(row)
    try:
        db.flush()
        db.add(
            ParkingLot(building_id=row.id, settings=default_settings(row).model_dump(mode="json"))
        )
        db.add(
            AuditLog(
                building_id=row.id,
                user_id=actor.id,
                action="CREATE_BUILDING",
                entity_type="Building",
                entity_id=str(row.id),
                old_value=None,
                new_value=BuildingPublic.model_validate(row).model_dump(mode="json"),
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409, code="DUPLICATE_BUILDING", message="Building code already exists."
        ) from exc
    return row


@router.patch("/{building_id}", response_model=BuildingPublic)
def set_building_state(building_id: UUID, payload: BuildingState, db: Db, actor: SystemAdmin):
    row = db.get(Building, building_id)
    if row is None:
        raise AppError(status_code=404, code="NOT_FOUND", message="Building not found.")
    before = BuildingPublic.model_validate(row).model_dump(mode="json")
    row.is_active = payload.is_active
    db.add(
        AuditLog(
            building_id=row.id,
            user_id=actor.id,
            action="UPDATE_BUILDING",
            entity_type="Building",
            entity_id=str(row.id),
            old_value=before,
            new_value=BuildingPublic.model_validate(row).model_dump(mode="json"),
        )
    )
    db.commit()
    return row


@router.post("/{building_id}/admins", status_code=201)
def create_building_admin(
    building_id: UUID, payload: BuildingAdminCreate, db: Db, actor: SystemAdmin, response: Response
):
    row = db.get(Building, building_id)
    if row is None or not row.is_active:
        raise AppError(status_code=404, code="NOT_FOUND", message="Active building not found.")
    temporary_password = secrets.token_urlsafe(18)
    response.headers["Cache-Control"] = "no-store"
    user = UserManagementService(db).create(
        UserCreate(
            username=payload.username,
            display_name=payload.display_name,
            email=payload.email,
            password=temporary_password,
            role=RoleName.BUILDING_ADMIN,
            building_id=building_id,
        ),
        actor,
    )
    return {"user": user, "temporary_password": temporary_password}
