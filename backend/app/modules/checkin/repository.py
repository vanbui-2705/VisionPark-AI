from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.modules.alpr.models import Detection
from app.modules.lanes.models import Lane

from .models import ParkingTransaction, TransactionStatus


class CheckInRepository(ABC):
    @abstractmethod
    def get_lane(self, lane_id: UUID) -> Lane | None:
        raise NotImplementedError

    @abstractmethod
    def get_detection(self, detection_id: UUID) -> Detection | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_idempotency_key(self, key: str) -> ParkingTransaction | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, transaction_id: UUID) -> ParkingTransaction | None:
        raise NotImplementedError

    @abstractmethod
    def get_active_by_plate(self, normalized_plate: str) -> ParkingTransaction | None:
        raise NotImplementedError

    @abstractmethod
    def save_transaction(self, values: dict) -> ParkingTransaction:
        raise NotImplementedError

    @abstractmethod
    def list_transactions(
        self,
        *,
        query: str | None = None,
        lane_id: UUID | None = None,
        status: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ParkingTransaction]:
        raise NotImplementedError


class DatabaseCheckInRepository(CheckInRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_lane(self, lane_id: UUID) -> Lane | None:
        return self.session.get(Lane, lane_id)

    def get_detection(self, detection_id: UUID) -> Detection | None:
        return self.session.get(Detection, detection_id)

    def get_by_idempotency_key(self, key: str) -> ParkingTransaction | None:
        stmt = (
            select(ParkingTransaction)
            .options(
                joinedload(ParkingTransaction.lane),
                joinedload(ParkingTransaction.check_in_operator),
            )
            .where(ParkingTransaction.idempotency_key == key)
        )
        return self.session.scalar(stmt)

    def get_by_id(self, transaction_id: UUID) -> ParkingTransaction | None:
        stmt = (
            select(ParkingTransaction)
            .options(
                joinedload(ParkingTransaction.lane),
                joinedload(ParkingTransaction.check_in_operator),
            )
            .where(ParkingTransaction.id == transaction_id)
        )
        return self.session.scalar(stmt)

    def get_active_by_plate(self, normalized_plate: str) -> ParkingTransaction | None:
        stmt = (
            select(ParkingTransaction)
            .options(
                joinedload(ParkingTransaction.lane),
                joinedload(ParkingTransaction.check_in_operator),
            )
            .where(
                ParkingTransaction.normalized_plate == normalized_plate,
                ParkingTransaction.status == TransactionStatus.PARKED,
            )
        )
        return self.session.scalar(stmt)

    def save_transaction(self, values: dict) -> ParkingTransaction:
        transaction = ParkingTransaction(**values)
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def list_transactions(
        self,
        *,
        query: str | None = None,
        lane_id: UUID | None = None,
        status: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ParkingTransaction]:
        stmt = (
            select(ParkingTransaction)
            .options(
                joinedload(ParkingTransaction.lane),
                joinedload(ParkingTransaction.check_in_operator),
            )
            .order_by(ParkingTransaction.check_in_time.desc())
            .limit(limit)
            .offset(offset)
        )
        if query:
            pattern = f"%{query.upper()}%"
            stmt = stmt.where(
                or_(
                    ParkingTransaction.license_plate.ilike(pattern),
                    ParkingTransaction.normalized_plate.ilike(pattern),
                )
            )
        if lane_id:
            stmt = stmt.where(ParkingTransaction.lane_id == lane_id)
        if status:
            stmt = stmt.where(ParkingTransaction.status == status)
        if from_time:
            stmt = stmt.where(ParkingTransaction.check_in_time >= from_time)
        if to_time:
            stmt = stmt.where(ParkingTransaction.check_in_time <= to_time)
        return list(self.session.scalars(stmt).all())


class FakeCheckInRepository(CheckInRepository):
    """Small in-memory repository retained for isolated service tests."""

    def __init__(self):
        self._fake_db: list[ParkingTransaction] = []

    def get_lane(self, lane_id: UUID) -> Lane | None:
        return Lane(
            id=lane_id,
            name="TEST_IN",
            direction="IN",
            video_source="fixture",
            is_active=True,
        )

    def get_detection(self, detection_id: UUID) -> Detection | None:
        return None

    def get_by_idempotency_key(self, key: str) -> ParkingTransaction | None:
        return next((item for item in self._fake_db if item.idempotency_key == key), None)

    def get_by_id(self, transaction_id: UUID) -> ParkingTransaction | None:
        return next((item for item in self._fake_db if item.id == transaction_id), None)

    def get_active_by_plate(self, normalized_plate: str) -> ParkingTransaction | None:
        return next(
            (
                item
                for item in self._fake_db
                if item.normalized_plate == normalized_plate
                and item.status == TransactionStatus.PARKED
            ),
            None,
        )

    def save_transaction(self, values: dict) -> ParkingTransaction:
        transaction = ParkingTransaction(id=uuid4(), **values)
        self._fake_db.append(transaction)
        return transaction

    def list_transactions(self, **kwargs) -> list[ParkingTransaction]:
        return list(self._fake_db)
