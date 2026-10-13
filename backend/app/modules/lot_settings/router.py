from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_permissions
from app.modules.lot_settings.contracts import no_pricing_provider
from app.modules.lot_settings.schemas import SettingsCopy, SettingsPublic, SettingsUpdate
from app.modules.lot_settings.service import configuration, load_lot, read_settings, write_settings
from app.modules.users.models import User

router = APIRouter(tags=["lot-settings"])
Db = Annotated[Session, Depends(get_db)]
Editor = Annotated[User, Depends(require_permissions("manage_settings"))]
Copier = Annotated[User, Depends(require_permissions("copy_settings"))]


def selected_building(db, actor, requested):
    if actor.role.name == "SYSTEM_ADMIN":
        if requested is None:
            raise AppError(status_code=422, code="BUILDING_REQUIRED", message="Select a building.")
        return requested
    if requested is not None:
        raise AppError(
            status_code=403,
            code="BUILDING_ACCESS_DENIED",
            message="Building is resolved from your account.",
        )
    return db.info["building_id"]


@router.get("/settings/lot", response_model=SettingsPublic)
def get_lot_settings(request: Request, db: Db, actor: CurrentUser, building_id: UUID | None = None):
    return read_settings(
        db,
        selected_building(db, actor, building_id),
        getattr(request.app.state, "effective_pricing", no_pricing_provider),
    )


@router.put("/settings/lot", response_model=SettingsPublic)
def put_lot_settings(payload: SettingsUpdate, request: Request, db: Db, actor: Editor):
    building_id = db.info["building_id"]
    write_settings(db, actor, building_id, payload)
    return read_settings(
        db, building_id, getattr(request.app.state, "effective_pricing", no_pricing_provider)
    )


@router.post("/buildings/{source_building_id}/copy-settings", response_model=SettingsPublic)
def copy_lot_settings(
    source_building_id: UUID, payload: SettingsCopy, request: Request, db: Db, actor: Copier
):
    if source_building_id == payload.target_building_id:
        raise AppError(
            status_code=422,
            code="INVALID_COPY_TARGET",
            message="Select a different target building.",
        )
    # Consistent lock order prevents reciprocal copies deadlocking on PostgreSQL.
    lots = {
        key: load_lot(db, key, lock=True)
        for key in sorted([source_building_id, payload.target_building_id])
    }
    source_building, source = lots[source_building_id]
    target_building, target = lots[payload.target_building_id]
    if source.settings_revision != payload.source_revision:
        raise AppError(
            status_code=409,
            code="SETTINGS_CONFLICT",
            message="Source settings changed. Reload before copying.",
        )
    copied = configuration(source_building, source).model_copy(deep=True)
    current = configuration(target_building, target)
    # Preserve target identity, PCCC contacts/locations and physical lane/device IDs.
    copied.information = current.information
    copied.fire = current.fire
    write_settings(
        db,
        actor,
        target_building.id,
        SettingsUpdate(revision=payload.target_revision, settings=copied),
        "COPY_LOT_SETTINGS",
        source_building_id,
    )
    return read_settings(
        db, target_building.id, getattr(request.app.state, "effective_pricing", no_pricing_provider)
    )
