"""Building-scoped daily aggregation from real parking transactions and paid invoices."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.buildings.models import Building
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.m5.models import DailyStat
from app.modules.pricing.models import Invoice, Payment


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def aggregate_day(db: Session, building_id, day: date) -> DailyStat:
    building = db.get(Building, building_id)
    if building is None:
        raise ValueError("Unknown building")
    zone = ZoneInfo(building.timezone)
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=zone).astimezone(
        UTC
    )
    entries = (
        db.scalar(
            select(func.count())
            .select_from(ParkingTransaction)
            .where(
                ParkingTransaction.building_id == building_id,
                ParkingTransaction.check_in_time >= start,
                ParkingTransaction.check_in_time < end,
            )
        )
        or 0
    )
    exits = (
        db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.building_id == building_id,
                Invoice.check_out_time >= start,
                Invoice.check_out_time < end,
            )
        )
        or 0
    )
    # Count settled payments only; refunds are excluded rather than silently netted.
    revenue = (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount_vnd), 0)).where(
                Payment.building_id == building_id,
                Payment.status == "PAID",
                Payment.confirmed_at >= start,
                Payment.confirmed_at < end,
            )
        )
        or 0
    )
    overlapping = list(
        db.scalars(
            select(ParkingTransaction).where(
                ParkingTransaction.building_id == building_id,
                ParkingTransaction.check_in_time < end,
                ParkingTransaction.status != TransactionStatus.CANCELLED.value,
                (ParkingTransaction.exit_time.is_(None) | (ParkingTransaction.exit_time >= start)),
            )
        )
    )
    occupancy = sum(1 for tx in overlapping if _as_utc(tx.check_in_time) < start)
    occupancy_peak = occupancy
    events: list[tuple[datetime, int]] = []
    for tx in overlapping:
        check_in = _as_utc(tx.check_in_time)
        exit_time = _as_utc(tx.exit_time) if tx.exit_time is not None else None
        if start <= check_in < end:
            events.append((check_in, 1))
        if exit_time is not None and start <= exit_time < end:
            events.append((exit_time, -1))
    # At an identical timestamp process exits first so a transferred bay is not double-counted.
    for _, delta in sorted(events, key=lambda event: (event[0], event[1])):
        occupancy = max(0, occupancy + delta)
        occupancy_peak = max(occupancy_peak, occupancy)
    row = db.scalar(
        select(DailyStat)
        .where(
            DailyStat.building_id == building_id,
            DailyStat.stat_date == day,
            DailyStat.vehicle_type == "ALL",
        )
        .with_for_update()
    )
    if row is None:
        row = DailyStat(building_id=building_id, stat_date=day, vehicle_type="ALL")
        db.add(row)
    row.entries = entries
    row.exits = exits
    row.revenue = revenue
    row.occupancy_peak = occupancy_peak
    db.flush()
    return row
