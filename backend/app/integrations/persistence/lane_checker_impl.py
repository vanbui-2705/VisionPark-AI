"""Lane adapter using the shared request session."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.lanes.models import Lane


class DatabaseLaneChecker:
    def __init__(self, session: Session):
        self.session = session

    def check_active_lane(self, lane_id: str) -> bool:
        try:
            parsed_id = UUID(lane_id)
        except ValueError:
            return False
        return (
            self.session.scalar(
                select(Lane.id).where(Lane.id == parsed_id, Lane.is_active.is_(True))
            )
            is not None
        )
