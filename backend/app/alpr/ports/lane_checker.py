from abc import ABC, abstractmethod


class ActiveLaneChecker(ABC):
    """
    Cổng (Port) để kiểm tra xem một làn xe có đang hoạt động và hợp lệ để xử lý ALPR hay không."""

    @abstractmethod
    def check_active_lane(self, lane_id: str) -> bool:
        """Trả về True nếu làn xe tồn tại và đang hoạt động, ngược lại trả về False."""
        pass
