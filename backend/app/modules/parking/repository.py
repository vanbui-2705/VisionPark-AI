from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.parking.models import ParkingTransaction, TransactionStatus


def list_transactions(
    db: Session,
    *,
    q: str | None = None,
    lane_id: UUID | None = None,
    status: TransactionStatus | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    page: int = 0,
    pageSize: int = 20,
) -> tuple[list[ParkingTransaction], int]:
    query = select(ParkingTransaction)
    count_q = select(func.count()).select_from(ParkingTransaction)

    filters = []
    if q:
        filters.append(ParkingTransaction.license_plate.ilike(f"%{q}%"))
    if lane_id:
        filters.append(ParkingTransaction.lane_id == lane_id)
    if status:
        filters.append(ParkingTransaction.status == status)
    if from_time:
        filters.append(ParkingTransaction.check_in_time >= from_time)
    if to_time:
        filters.append(ParkingTransaction.check_in_time <= to_time)

    for f in filters:
        query = query.where(f)
        count_q = count_q.where(f)

    total = db.scalar(count_q) or 0
    items = list(db.scalars(query.order_by(ParkingTransaction.check_in_time.desc()).offset(page * pageSize).limit(pageSize)).all())
    return items, total


def get_transaction(db: Session, tid: UUID) -> ParkingTransaction | None:
    return db.scalar(select(ParkingTransaction).where(ParkingTransaction.id == tid))
