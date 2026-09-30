from app.core.errors import AppError
from app.modules.checkin.repository import CheckInRepository
from app.modules.checkin.schemas import CheckInRequest, CheckInResponse


class CheckInService:
    # Nhúng (Inject) Repository vào Service thông qua Interface
    def __init__(self, repository: CheckInRepository):
        self.repo = repository

    def process_check_in(
        self, request: CheckInRequest, is_lane_active: bool, lane_type: str
    ) -> CheckInResponse:

        # 0. CHỐNG DOUBLE CLICK (IDEMPOTENCY) ƯU TIÊN SỐ 1
        existing_tx = self.repo.get_by_idempotency_key(request.idempotency_key)
        if existing_tx:
            # Trả về vé cũ luôn, không báo lỗi trùng biển số
            return CheckInResponse(**existing_tx)

        # 1. KIỂM TRA LÀN XE (Task P2-BD-003)
        if not is_lane_active:
            raise AppError(
                status_code=400,
                code="LANE_INACTIVE",
                message="Làn xe này đang bảo trì hoặc bị khóa.",
            )
        if lane_type != "IN":
            raise AppError(
                status_code=400,
                code="INVALID_LANE_TYPE",
                message="Xe đang đứng ở cổng RA, không thể Check-in.",
            )

        # 2. KIỂM TRA VÀ CHUẨN HÓA BIỂN SỐ (Task P2-BD-003)
        # Chuẩn hóa: Cắt khoảng trắng, xóa dấu gạch ngang, xóa dấu chấm, chuyển thành chữ IN HOA
        plate = (
            request.plate_number.replace("-", "").replace(".", "").replace(" ", "").strip().upper()
        )

        if len(plate) < 3:
            raise AppError(
                status_code=400, code="INVALID_PLATE", message="Biển số quá ngắn hoặc không hợp lệ."
            )

        # 3. CHỐNG XE TRỐN VÉ / ĐỖ TRÙNG (Task P2-BD-004)
        if self.repo.is_plate_parked(plate):
            raise AppError(
                status_code=409,
                code="PLATE_ALREADY_PARKED",
                message=f"Xe mang biển số {plate} đang nằm trong bãi, không thể Check-in lần 2.",
            )

        # 4. TẠO GIAO DỊCH VÀO BÃI (Task P2-BD-002)
        # Service không tự lưu, mà gọi Hợp đồng (Repo) để lưu
        tx_data = self.repo.save_transaction(
            lane_id=request.lane_id, plate_number=plate, idempotency_key=request.idempotency_key
        )

        # Trả về kết quả chuẩn để Frontend hiển thị
        return CheckInResponse(**tx_data)
