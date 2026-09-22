from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Lane


def get_lane_by_id(db: Session, lane_id: UUID) -> Lane | None:
    """Lấy lane theo ID."""
    stmt = select(Lane).where(Lane.id == lane_id)
    return db.scalar(stmt)


def get_lane_by_name(db: Session, name: str) -> Lane | None:
    """Lấy lane theo tên để kiểm tra duplicate."""
    stmt = select(Lane).where(Lane.name == name)
    return db.scalar(stmt)


def get_all_lanes(db: Session) -> list[Lane]:
    """Lấy tất cả lane."""
    stmt = select(Lane)
    return list(db.scalars(stmt).all())


def create_lane(db: Session, lane_data: dict) -> Lane:
    """Tạo lane mới từ dictionary dữ liệu."""
    db_lane = Lane(**lane_data)
    db.add(db_lane)
    db.commit()
    db.refresh(db_lane)
    return db_lane


def update_lane(db: Session, db_lane: Lane, update_data: dict) -> Lane:
    """Cập nhật thông tin lane."""
    for key, value in update_data.items():
        if value is not None:
            setattr(db_lane, key, value)
    db.commit()
    db.refresh(db_lane)
    return db_lane


def list_active_lanes(db: Session) -> list[Lane]:
    """Lấy danh sách lane đang active."""
    stmt = select(Lane).where(Lane.is_active.is_(True))
    return list(db.scalars(stmt).all())
