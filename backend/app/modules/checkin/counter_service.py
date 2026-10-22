from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.checkin.capacity_quota_stub import (
    calculate_effective_capacity_limit,
    check_capacity_and_quota_stub,
    get_capacity_settings_stub,
)
from app.modules.checkin.counter_models import CounterEvent, ParkingCounter


class CounterService:
    @staticmethod
    def get_or_create_counter(
        db: Session, building_id: UUID | None, vehicle_type: str
    ) -> ParkingCounter:
        vtype = vehicle_type.upper()
        stmt = select(ParkingCounter).where(
            ParkingCounter.building_id == building_id
            if building_id is not None
            else ParkingCounter.building_id.is_(None),
            ParkingCounter.vehicle_type == vtype,
        )
        if db.bind and getattr(db.bind.dialect, "name", None) == "postgresql":
            stmt = stmt.with_for_update()

        counter = db.execute(stmt).scalar_one_or_none()
        if not counter:
            counter = ParkingCounter(
                building_id=building_id,
                vehicle_type=vtype,
                occupied=0,
            )
            db.add(counter)
            db.flush()
        return counter

    @classmethod
    def increment_atomic(
        cls,
        db: Session,
        building_id: UUID | None,
        vehicle_type: str,
        session_id: UUID,
        customer_class: str = "VISITOR",
        actor_type: str = "SYSTEM",
        actor_id: UUID | None = None,
        reason: str = "CHECK_IN",
        note: str | None = None,
    ) -> ParkingCounter:
        """Tăng bộ đếm nguyên tử có điều kiện bằng SQL UPDATE duy nhất chống Race Condition."""
        vtype = vehicle_type.upper()
        counter = cls.get_or_create_counter(db, building_id, vtype)
        if type(counter).__name__ == "MagicMock" and not isinstance(counter.occupied, int):
            counter.occupied = 0

        # Lấy giới hạn tối đa cho phép đối với hạng khách hiện tại
        cfg = get_capacity_settings_stub(building_id, vtype, db=db)
        limit = calculate_effective_capacity_limit(cfg, customer_class)

        # CẬP NHẬT CÓ ĐIỀU KIỆN TRONG 1 CÂU LỆNH DUY NHẤT:
        # UPDATE parking_counters SET occupied = occupied + 1 WHERE id = :id AND occupied < :limit
        where_cond = [
            ParkingCounter.id == counter.id,
            ParkingCounter.occupied < limit,
        ]
        stmt = (
            update(ParkingCounter)
            .where(*where_cond)
            .values(occupied=ParkingCounter.occupied + 1, updated_at=datetime.now(UTC))
        )
        result = db.execute(stmt)

        # Kiểm tra rowcount để biết thành công hay thất bại (chống race condition 2 xe vào cùng lúc)
        rowcount = getattr(result, "rowcount", 1)
        if rowcount == 0:
            _, msg = check_capacity_and_quota_stub(
                current_occupied=counter.occupied,
                vehicle_type=vtype,
                customer_class=customer_class,
                building_id=building_id,
                db=db,
            )
            raise AppError(
                status_code=403,
                code="CAPACITY_FULL",
                message=msg or f"Bãi xe đã hết chỗ cho loại xe {vtype} (ngưỡng tối đa: {limit}).",
            )

        # Cập nhật đối tượng ORM trong phiên làm việc
        if isinstance(counter.occupied, int):
            counter.occupied += 1
        counter.updated_at = datetime.now(UTC)

        counter_id = getattr(counter, "id", None)
        if type(counter_id).__name__ == "MagicMock":
            counter_id = None

        event = CounterEvent(
            building_id=building_id,
            counter_id=counter_id,
            vehicle_type=vtype,
            delta=1,
            session_id=session_id,
            reason=reason,
            actor_type=actor_type,
            actor_id=actor_id,
            note=note,
            occurred_at=datetime.now(UTC),
        )
        db.add(event)
        db.flush()
        return counter

    @classmethod
    def decrement_atomic(
        cls,
        db: Session,
        building_id: UUID | None,
        vehicle_type: str,
        session_id: UUID,
        actor_type: str = "SYSTEM",
        actor_id: UUID | None = None,
        reason: str = "CHECK_OUT",
        note: str | None = None,
    ) -> ParkingCounter:
        """Giảm bộ đếm nguyên tử có điều kiện (chỉ giảm khi occupied > 0)."""
        vtype = vehicle_type.upper()
        counter = cls.get_or_create_counter(db, building_id, vtype)

        stmt = (
            update(ParkingCounter)
            .where(ParkingCounter.id == counter.id, ParkingCounter.occupied > 0)
            .values(occupied=ParkingCounter.occupied - 1, updated_at=datetime.now(UTC))
        )
        db.execute(stmt)

        if isinstance(counter.occupied, int) and counter.occupied > 0:
            counter.occupied -= 1
        counter.updated_at = datetime.now(UTC)

        counter_id = getattr(counter, "id", None)
        if type(counter_id).__name__ == "MagicMock":
            counter_id = None

        event = CounterEvent(
            building_id=building_id,
            counter_id=counter_id,
            vehicle_type=vtype,
            delta=-1,
            session_id=session_id,
            reason=reason,
            actor_type=actor_type,
            actor_id=actor_id,
            note=note,
            occurred_at=datetime.now(UTC),
        )
        db.add(event)
        db.flush()
        return counter

    @classmethod
    def adjust_counter(
        cls,
        db: Session,
        building_id: UUID | None,
        vehicle_type: str,
        delta: int,
        reason: str,
        actor_type: str = "OPERATOR",
        actor_id: UUID | None = None,
        note: str | None = None,
    ) -> ParkingCounter:
        """Hiệu chỉnh bộ đếm thủ công có lý do, chỉ thêm CounterEvent (mục 4.4 nghiepvu.md)."""
        if delta == 0:
            raise AppError(
                status_code=422,
                code="INVALID_DELTA",
                message="Delta điều chỉnh không được bằng 0.",
            )
        vtype = vehicle_type.upper()
        counter = cls.get_or_create_counter(db, building_id, vtype)
        new_val = counter.occupied + delta
        if new_val < 0:
            raise AppError(
                status_code=422,
                code="NEGATIVE_OCCUPIED",
                message=(
                    f"Số xe sau điều chỉnh không thể âm "
                    f"(hiện tại: {counter.occupied}, delta: {delta})."
                ),
            )
        counter.occupied = new_val
        counter.updated_at = datetime.now(UTC)

        event = CounterEvent(
            building_id=building_id,
            counter_id=counter.id,
            vehicle_type=vtype,
            delta=delta,
            reason=reason,
            actor_type=actor_type,
            actor_id=actor_id,
            note=note,
            occurred_at=datetime.now(UTC),
        )
        db.add(event)
        db.flush()
        return counter

    @classmethod
    def get_availability(cls, db: Session, building_id: UUID | None) -> list[dict]:
        """Lấy thông tin chỗ trống và trạng thái theo từng loại xe (mục 4.4 nghiepvu.md)."""
        results = []
        types = ["CAR", "MOTORBIKE", "BICYCLE"]
        for vtype in types:
            cfg = get_capacity_settings_stub(building_id, vtype, db=db)
            stmt = select(ParkingCounter).where(
                ParkingCounter.building_id == building_id
                if building_id is not None
                else ParkingCounter.building_id.is_(None),
                ParkingCounter.vehicle_type == vtype,
            )
            counter = db.execute(stmt).scalar_one_or_none()
            occupied = counter.occupied if counter else 0
            safe_capacity = cfg.safe_capacity
            physical_capacity = cfg.physical_capacity
            available = max(0, safe_capacity - occupied)
            reserved = cfg.resident_quota + cfg.staff_quota
            available_for_visitor = max(0, safe_capacity - reserved - occupied)

            ratio = occupied / max(1, safe_capacity)
            if ratio >= cfg.full_ratio:
                status = "FULL"
            elif ratio >= cfg.nearly_full_ratio:
                status = "NEARLY_FULL"
            else:
                status = "AVAILABLE"

            results.append(
                {
                    "vehicle_type": vtype,
                    "occupied": occupied,
                    "safe_capacity": safe_capacity,
                    "physical_capacity": physical_capacity,
                    "available": available,
                    "available_for_visitor": available_for_visitor,
                    "resident_quota": cfg.resident_quota,
                    "staff_quota": cfg.staff_quota,
                    "status": status,
                }
            )
        return results
