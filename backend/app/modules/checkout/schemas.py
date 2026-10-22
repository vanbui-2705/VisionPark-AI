from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.checkin.schemas import ParkingTransactionResponse


class CheckOutRequest(BaseModel):
    """Request đóng phiên gửi xe — idempotent qua idempotency_key."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Định danh phiên: ID phiên, biển số chuẩn hoặc mã vé xe đạp
    session_id: UUID | None = Field(None, description="ID phiên gửi xe nếu đã có từ preview")
    license_plate: str | None = Field(
        None, min_length=1, max_length=50, description="Biển số (đã hoặc chưa chuẩn hóa)"
    )
    ticket_code: str | None = Field(None, min_length=3, max_length=64, description="Mã vé xe đạp")

    # Làn ra
    exit_lane_id: UUID = Field(..., description="ID làn OUT")

    # Ảnh ra (URL từ ALPR hoặc camera tại cổng ra)
    exit_image_url: str | None = Field(None, max_length=512)

    # Loại xe nhận diện tại cổng ra (để cảnh báo lệch loại)
    vehicle_type_out: str | None = Field(
        None, description="Loại xe nhận diện khi ra (cảnh báo lệch loại)"
    )

    # Thanh toán tại chỗ nếu có phí (vd: CASH, VIETQR_MOCK)
    payment_method: str | None = Field(
        None, description="Phương thức thanh toán trực tiếp tại cổng ra nếu có phí"
    )

    # Override: bảo vệ ghi lý do cho các trường hợp ngoại lệ
    override_reason: str | None = Field(None, max_length=500)
    is_lost_ticket: bool = Field(False, description="True nếu mất vé/thẻ — áp phí mất vé")

    # Idempotency
    idempotency_key: str | None = Field(None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_identification(self) -> "CheckOutRequest":
        if not self.session_id and not self.license_plate and not self.ticket_code:
            raise ValueError("session_id, license_plate hoặc ticket_code là bắt buộc")
        return self


class PaymentRecordRequest(BaseModel):
    """Request ghi nhận thu tiền mặt hoặc override thanh toán cho phiên đang chờ."""

    payment_method: str = Field(default="CASH", description="CASH | VIETQR_MOCK | CARD | OVERRIDE")
    amount: float = Field(ge=0.0, description="Số tiền thanh toán")
    provider_ref: str | None = Field(None, max_length=100, description="Mã giao dịch đối tác")
    override_reason: str | None = Field(
        None, max_length=500, description="Lý do nếu override miễn phí"
    )


class CheckOutPreviewResponse(BaseModel):
    """Kết quả preview tính phí — chưa thay đổi trạng thái phiên."""

    session_id: UUID
    license_plate: str | None = None
    ticket_code: str | None = None
    vehicle_type_in: str
    vehicle_type_out: str | None = None
    vehicle_type_mismatch: bool = False
    check_in_time: datetime
    check_in_image_url: str | None = None
    exit_image_url: str | None = None
    duration_minutes: int
    fee: float
    fee_lines: list[dict] | None = None
    price_snapshot: dict | None = None
    fee_breakdown: dict | None = None
    status: str
    message: str = ""


class CheckOutResponse(BaseModel):
    """Kết quả sau khi đóng phiên hoàn toàn."""

    transaction: ParkingTransactionResponse
    fee: float
    fee_lines: list[dict] | None = None
    fee_breakdown: dict | None = None
    status: str  # COMPLETED | PAID | EXITED | PAYMENT_PENDING
    barrier_opened: bool
    vehicle_type_mismatch: bool = False
    message: str
