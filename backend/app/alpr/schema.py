from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: int = Field(..., description="Tọa độ X góc trên cùng bên trái")
    y1: int = Field(..., description="Tọa độ Y góc trên cùng bên trái")
    x2: int = Field(..., description="Tọa độ X góc dưới cùng bên phải")
    y2: int = Field(..., description="Tọa độ Y góc dưới cùng bên phải")

    @property
    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class ALPRResult(BaseModel):
    plate_number: str | None = Field(None, description="Chuỗi biển số xe đọc được")
    bbox: BoundingBox | None = Field(None, description="Hộp bao quanh biển số xe (Bounding Box)")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy tổng thể của kết quả nhận diện (0.0 đến 1.0)",
    )
    processing_time_ms: int = Field(..., description="Thời gian xử lý ảnh tính bằng mili-giây")
    requires_confirmation: bool = Field(
        ..., description="True nếu độ tin cậy thấp hơn ngưỡng quy định, cần nhân viên xác nhận"
    )
    model_version: str = Field("unknown", description="Phiên bản model/provider đang chạy")
    detection_id: str | None = Field(None, description="ID detection sau khi persistence hoàn tất")


class ALPRHTTPResponse(BaseModel):
    raw_plate: str | None = Field(None, description="Biển số thô chưa xử lý")
    normalized_plate: str | None = Field(None, description="Biển số đã loại bỏ ký tự thừa")
    bbox: list[int] = Field(..., description="Tọa độ [x1, y1, x2, y2]")
    confidence: float
    latency_ms: float
    model_version: str
    requires_confirmation: bool = True
    detection_id: str | None = None

    # Compatibility fields used by the Station capture flow.
    raw_plate_number: str | None = None
    normalized_plate_number: str | None = None
    processing_time_ms: int | None = None
