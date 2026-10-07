from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import require_roles
from app.modules.checkin.repository import FakeCheckInRepository
from app.modules.checkin.schemas import CheckInRequest, CheckInResponse
from app.modules.checkin.service import CheckInService
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter()

# 1. KHỞI TẠO BỘ NHỚ GIẢ VÀ SERVICE
# (Chỉ duy nhất chỗ này biết đến sự tồn tại của chữ "Fake".
# Hôm sau Member 2 làm xong DB thật, ta chỉ việc đổi 1 dòng này thành RealRepository là xong).
fake_repo = FakeCheckInRepository()


def get_checkin_service():
    return CheckInService(repository=fake_repo)


# 2. ĐỊNH NGHĨA API POST /checkin
@router.post("/", response_model=CheckInResponse)
def create_checkin_ticket(
    request: CheckInRequest,
    service: CheckInService = Depends(get_checkin_service),
    # Bắt buộc người gọi API phải đăng nhập và có quyền Nhân viên (OPERATOR hoặc ADMIN)
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None,
):
    """
    API Mở Barrier cho xe vào bãi (Tạo vé Check-in).
    """

    # GIẢ LẬP KIỂM TRA LÀN XE TỪ DATABASE KHÁC
    # Đáng lý phải tra bảng Lanes xem request.lane_id có đúng là cổng VÀO (IN) không.
    # Tạm thời ta giả vờ là kết quả truy vấn trả về là hợp lệ để test luồng Check-in.
    mock_is_lane_active = True
    mock_lane_type = "IN"

    # Đẩy toàn bộ công việc khó cho Service xử lý
    return service.process_check_in(
        request=request, is_lane_active=mock_is_lane_active, lane_type=mock_lane_type, actor_id=current_user.id
    )


@router.get("/")
def get_parking_history(
    plate_number: str | None = None,
):
    """API Lấy lịch sử đỗ xe (Task 4.5)"""
    all_tx = fake_repo._fake_db
    if plate_number:
        all_tx = [tx for tx in all_tx if plate_number in tx.get("plate_number", "")]
    return all_tx
