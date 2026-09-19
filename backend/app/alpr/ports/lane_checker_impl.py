"""Concrete implementation of ActiveLaneChecker port."""
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from app.database.session import get_db
from app.modules.lanes.models import Lane


class DatabaseLaneChecker:
    """
    Implementation kiểm tra làn xe bằng cách query database.
    Đây là adapter kết nối giữa ALPR system và Lane domain.
    """
    
    def check_active_lane(self, lane_id: str) -> bool:
        """
        Kiểm tra lane tồn tại và đang active.
        
        Args:
            lane_id: ID của lane cần kiểm tra
            
        Returns:
            True nếu lane tồn tại và active, False ngược lại
        """
        # Sử dụng SQLAlchemy session để query
        from app.database.session import SessionLocal
        
        with SessionLocal() as db:
            result = db.execute(
                select(Lane).where(
                    Lane.id == lane_id,
                    Lane.is_active == True
                )
            )
            lane = result.scalar_one_or_none()
            return lane is not None