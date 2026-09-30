from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID, uuid4


# 1. (Interface)
class CheckInRepository(ABC):
    @abstractmethod
    def is_plate_parked(self, plate_number: str) -> bool:
        pass

    @abstractmethod
    def save_transaction(self, lane_id: UUID, plate_number: str, idempotency_key: str) -> dict:
        pass

    @abstractmethod
    def get_by_idempotency_key(self, key: str) -> dict | None:
        pass


# 2. GIẢ LẬP DATABASE (Fake Repository)
class FakeCheckInRepository(CheckInRepository):
    def __init__(self):
        # Dùng một mảng (List) trên RAM để đóng vai trò làm Database tạm thời
        self._fake_db = []

    def is_plate_parked(self, plate_number: str) -> bool:
        # Quét DB: Tìm xem có vé nào biển số này mà trạng thái vẫn đang đỗ (PARKED) không
        for tx in self._fake_db:
            if tx["plate_number"] == plate_number and tx["status"] == "PARKED":
                return True
        return False

    def get_by_idempotency_key(self, key: str) -> dict | None:
        for tx in self._fake_db:
            if tx.get("idempotency_key") == key:
                return tx
        return None

    def save_transaction(self, lane_id: UUID, plate_number: str, idempotency_key: str) -> dict:
        # 1. CƠ CHẾ CHỐNG RUNG TAY / LỖI MẠNG (Idempotency)
        for existing_tx in self._fake_db:
            if existing_tx.get("idempotency_key") == idempotency_key:
                # Gửi trùng mã -> Trả về luôn cái vé đã tạo lúc nãy, không tạo vé mới
                return existing_tx

        # 2. TẠO VÉ MỚI (Lưu vào DB giả)
        new_tx = {
            "transaction_id": uuid4(),
            "plate_number": plate_number,
            "lane_id": lane_id,
            "check_in_time": datetime.utcnow(),
            "status": "PARKED",
            "idempotency_key": idempotency_key,
        }
        self._fake_db.append(new_tx)
        return new_tx
