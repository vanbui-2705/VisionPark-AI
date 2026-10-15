from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit_logs.service import log_action
from app.modules.checkin.counter_models import ParkingCounter
from app.modules.checkin.counter_service import CounterService
from app.modules.checkin.models import ParkingTransaction, TransactionStatus


@dataclass
class DiscrepancyDetail:
    vehicle_type: str
    counter_occupied: int
    active_sessions: int
    drift: int  # active_sessions - counter_occupied


class CounterReconciliationService:
    @staticmethod
    def get_active_session_counts(db: Session, building_id: UUID | None) -> dict[str, int]:
        """Đếm số phiên PARKED thực tế theo từng loại xe trong parking_transactions."""
        stmt = (
            select(
                ParkingTransaction.vehicle_type,
                func.count(ParkingTransaction.id).label("active_count"),
            )
            .where(
                ParkingTransaction.building_id == building_id,
                ParkingTransaction.status == TransactionStatus.PARKED,
            )
            .group_by(ParkingTransaction.vehicle_type)
        )
        rows = db.execute(stmt).all()
        return {r[0].upper(): int(r[1]) for r in rows if r[0]}

    @classmethod
    def check_discrepancies(cls, db: Session, building_id: UUID | None) -> list[DiscrepancyDetail]:
        """So sánh số phiên đang mở với bộ đếm và phát hiện sai lệch (mục 4.4 nghiepvu.md)."""
        active_counts = cls.get_active_session_counts(db, building_id)
        discrepancies: list[DiscrepancyDetail] = []
        types = ["CAR", "MOTORBIKE", "BICYCLE"]

        for vtype in types:
            counter = CounterService.get_or_create_counter(db, building_id, vtype)
            # Safeguard in case occupied is mock
            occupied = counter.occupied if isinstance(counter.occupied, int) else 0
            actual_active = active_counts.get(vtype, 0)
            drift = actual_active - occupied
            if drift != 0:
                discrepancies.append(
                    DiscrepancyDetail(
                        vehicle_type=vtype,
                        counter_occupied=occupied,
                        active_sessions=actual_active,
                        drift=drift,
                    )
                )
        return discrepancies

    @classmethod
    def reconcile_and_adjust(
        cls,
        db: Session,
        building_id: UUID | None,
        auto_correct: bool = True,
        actor_type: str = "OPERATOR",
        actor_id: UUID | None = None,
        reason: str = "PERIODIC_RECONCILIATION",
    ) -> tuple[list[DiscrepancyDetail], bool]:
        """Chạy job đối soát, hiệu chỉnh qua counter_events có audit (mục 4.4 nghiepvu.md).

        Admin hiệu chỉnh qua counter_events — không sửa số trực tiếp.
        """
        discrepancies = cls.check_discrepancies(db, building_id)
        if not discrepancies or not auto_correct:
            return discrepancies, False

        for item in discrepancies:
            note = (
                f"Đối chiếu bộ đếm: trước={item.counter_occupied}, "
                f"thực tế={item.active_sessions}, delta={item.drift}"
            )
            counter = CounterService.adjust_counter(
                db=db,
                building_id=building_id,
                vehicle_type=item.vehicle_type,
                delta=item.drift,
                reason=reason,
                actor_type=actor_type,
                actor_id=actor_id,
                note=note,
            )

            if actor_id:
                log_action(
                    db=db,
                    user_id=actor_id,
                    action="RECONCILE_COUNTER",
                    entity_type="ParkingCounter",
                    entity_id=str(counter.id),
                    new_value={
                        "vehicle_type": item.vehicle_type,
                        "old_occupied": item.counter_occupied,
                        "new_occupied": counter.occupied,
                        "drift": item.drift,
                        "reason": reason,
                    },
                )
        db.commit()
        return discrepancies, True

    @classmethod
    def compensate_offline_session(
        cls,
        db: Session,
        building_id: UUID | None,
        vehicle_type: str,
        actor_id: UUID,
        session_id: UUID | None = None,
        reason: str = "NETWORK_OFFLINE_COMPENSATION",
        note: str | None = None,
    ) -> ParkingCounter:
        """Phiên bù khi mạng lỗi: tăng bộ đếm qua counter_events có audit (mục 4.4 nghiepvu.md)."""
        counter = CounterService.adjust_counter(
            db=db,
            building_id=building_id,
            vehicle_type=vehicle_type,
            delta=1,
            reason=reason,
            actor_type="OPERATOR",
            actor_id=actor_id,
            note=note or "Phiên bù khi mạng lỗi ghi nhận xe vào",
        )
        log_action(
            db=db,
            user_id=actor_id,
            action="COMPENSATE_SESSION",
            entity_type="ParkingCounter",
            entity_id=str(counter.id),
            new_value={
                "vehicle_type": vehicle_type,
                "delta": 1,
                "new_occupied": counter.occupied,
                "session_id": str(session_id) if session_id else None,
                "reason": reason,
                "note": note,
            },
        )
        db.commit()
        db.refresh(counter)
        return counter
