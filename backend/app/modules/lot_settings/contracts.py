"""M3/M4 handoff ports; missing integrations fail closed, never invent prices.

M4 registers a checker in app.state.effective_pricing. It must read committed,
building-owned pricing versions and return whether one applies at the UTC instant.
M3 adds vehicle_type to sessions. Until then legacy sessions count as CAR.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lot_settings.schemas import VehicleType

PricingChecker = Callable[[Session, UUID, datetime], bool]


def occupied_by_type(db: Session, building_id: UUID) -> dict[str, int]:
    counts = {kind.value: 0 for kind in VehicleType}
    vehicle_type = getattr(ParkingTransaction, "vehicle_type", None)
    query = select(ParkingTransaction).where(
        ParkingTransaction.building_id == building_id,
        ParkingTransaction.status == TransactionStatus.PARKED,
    )
    if vehicle_type is None:
        counts["CAR"] = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        return counts
    grouped = (
        select(vehicle_type, func.count())
        .where(
            ParkingTransaction.building_id == building_id,
            ParkingTransaction.status == TransactionStatus.PARKED,
        )
        .group_by(vehicle_type)
    )
    for vehicle, count in db.execute(grouped):
        kind = getattr(vehicle, "value", vehicle)
        if kind in counts:
            counts[kind] += count
        else:
            # Unknown sessions conservatively reserve a place in each capacity bucket.
            for key in counts:
                counts[key] += count
    return counts


def no_pricing_provider(db: Session, building_id: UUID, at: datetime) -> bool:
    return False
