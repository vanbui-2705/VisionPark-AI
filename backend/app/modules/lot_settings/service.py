from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import AppError
from app.modules.audit_logs.models import AuditLog
from app.modules.buildings.models import Building, ParkingLot, UserBuilding
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.lot_settings.contracts import PricingChecker, no_pricing_provider, occupied_by_type
from app.modules.lot_settings.schemas import (
    LotSettings,
    Readiness,
    SettingsPublic,
    default_settings,
)


def load_lot(db: Session, building_id: UUID, *, lock=False) -> tuple[Building, ParkingLot]:
    building = db.get(Building, building_id)
    query = select(ParkingLot).where(ParkingLot.building_id == building_id)
    if lock:
        query = query.with_for_update()
    lot = db.scalar(query)
    if building is None or lot is None:
        raise AppError(status_code=404, code="NOT_FOUND", message="Parking lot not found.")
    return building, lot


def configuration(building, lot) -> LotSettings:
    # Empty legacy configuration remains readable and is explicitly not ready.
    return LotSettings.model_validate(lot.settings) if lot.settings else default_settings(building)


def readiness(
    db: Session,
    building,
    settings: LotSettings,
    pricing: PricingChecker = no_pricing_provider,
    at: datetime | None = None,
) -> Readiness:
    now = at or datetime.now(UTC)
    missing = []
    if not building.is_active:
        missing.append("BUILDING_LOCKED")
    if settings.information.status != "OPEN":
        missing.append(f"LOT_{settings.information.status}")
    windows = settings.information.operating_hours
    local = now.astimezone(ZoneInfo(settings.information.timezone))
    if windows and not any(
        w.weekday == local.weekday() and w.start <= local.time() < w.end for w in windows
    ):
        missing.append("OUTSIDE_OPERATING_HOURS")
    if not any(c.safe_capacity > 0 for c in settings.capacities.values()):
        missing.append("CAPACITY_REQUIRED")
    directions = set(
        db.scalars(
            select(Lane.direction).where(Lane.building_id == building.id, Lane.is_active.is_(True))
        )
    )
    if LaneDirection.IN not in directions:
        missing.append("ACTIVE_IN_LANE_REQUIRED")
    if LaneDirection.OUT not in directions:
        missing.append("ACTIVE_OUT_LANE_REQUIRED")
    if pricing(db, building.id, now) is not True:
        missing.append("EFFECTIVE_PRICING_REQUIRED")
    return Readiness(ready=not missing, missing=missing)


def read_settings(db, building_id, pricing=no_pricing_provider):
    building, lot = load_lot(db, building_id)
    settings = configuration(building, lot)
    return SettingsPublic(
        building_id=building_id,
        revision=lot.settings_revision,
        settings=settings,
        readiness=readiness(db, building, settings, pricing),
    )


def validate_live_settings(db, building_id, settings):
    counts = occupied_by_type(db, building_id)
    for kind, capacity in settings.capacities.items():
        if capacity.safe_capacity < counts[kind.value]:
            raise AppError(
                status_code=409,
                code="CAPACITY_BELOW_OCCUPANCY",
                message=f"Safe capacity for {kind} cannot be below parked vehicles.",
                details={"vehicle_type": kind.value, "occupied": counts[kind.value]},
            )
    if settings.fire.alert_recipients:
        assigned = set(
            db.scalars(
                select(UserBuilding.user_id).where(
                    UserBuilding.building_id == building_id,
                    UserBuilding.user_id.in_(settings.fire.alert_recipients),
                )
            )
        )
        if assigned != set(settings.fire.alert_recipients):
            raise AppError(
                status_code=422,
                code="INVALID_ALERT_RECIPIENT",
                message="Alert recipients must belong to this building.",
            )


def write_settings(
    db, actor, building_id, payload, action="UPDATE_LOT_SETTINGS", source_building_id=None
):
    building, lot = load_lot(db, building_id, lock=True)
    if lot.settings_revision != payload.revision:
        raise AppError(
            status_code=409,
            code="SETTINGS_CONFLICT",
            message="Settings changed. Reload before saving.",
        )
    validate_live_settings(db, building_id, payload.settings)
    before = {
        "revision": lot.settings_revision,
        "settings": configuration(building, lot).model_dump(mode="json"),
    }
    lot.settings = payload.settings.model_dump(mode="json")
    lot.settings_revision += 1
    after = {"revision": lot.settings_revision, "settings": lot.settings}
    if source_building_id:
        after["copied_from_building_id"] = str(source_building_id)
    db.add(
        AuditLog(
            building_id=building_id,
            user_id=actor.id,
            action=action,
            entity_type="ParkingLot",
            entity_id=str(lot.id),
            old_value=before,
            new_value=after,
        )
    )
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise AppError(
            status_code=409,
            code="SETTINGS_CONFLICT",
            message="Settings changed. Reload before saving.",
        ) from exc


def require_ready_for_entry(db, building_id, pricing=no_pricing_provider):
    # This lock also serializes Setting capacity reductions with PostgreSQL entries.
    building, lot = load_lot(db, building_id, lock=True)
    result = readiness(db, building, configuration(building, lot), pricing)
    if not result.ready:
        raise AppError(
            status_code=409,
            code="LOT_NOT_READY",
            message="The parking lot is not ready to accept vehicles.",
            details={"missing": result.missing},
        )
