"""ALPR Detection model - lưu lịch sử nhận diện biển số."""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Detection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Bảng lưu lịch sử nhận diện biển số xe."""

    __tablename__ = "detections"

    # Foreign key đến Lane
    lane_id = Column(Uuid, ForeignKey("lanes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Thông tin ảnh & Media Metadata (VỪA THÊM)
    image_key = Column(
        String(255), nullable=False, index=True, comment="Storage key do ImageStorage trả về"
    )
    image_content_type = Column(String(50), default="image/jpeg", nullable=False)
    image_size_bytes = Column(Integer, nullable=True)

    # Dữ liệu AI đọc
    raw_plate = Column(String(50), nullable=True, index=True)
    normalized_plate = Column(String(50), nullable=True, index=True)
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    model_version = Column(String(120), nullable=True)
    capture_fingerprint = Column(String(64), nullable=True)

    # 4. Thông tin Xác nhận / Confirmation
    input_kind = Column(String(20), nullable=True, index=True)
    video_time_ms = Column(Integer, nullable=True)
    provider = Column(String(64), nullable=True)
    detector_confidence = Column(Float, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    combined_confidence = Column(Float, nullable=True)
    quality_flags = Column(JSON, nullable=True)
    detector_latency_ms = Column(Float, nullable=True)
    ocr_latency_ms = Column(Float, nullable=True)
    actor_id = Column(Uuid, ForeignKey("users.id"), nullable=True)
    lane_name_snapshot = Column(String(120), nullable=True)
    direction_snapshot = Column(String(10), nullable=True)

    @property
    def lane_name(self):
        return self.lane_name_snapshot or (self.lane.name if self.lane else None)

    @property
    def direction(self):
        return self.direction_snapshot or (self.lane.direction.value if self.lane else None)

    requires_confirmation = Column(Boolean, default=False, nullable=False)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_plate = Column(String(50), nullable=True)
    confirmed_by_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    lane = relationship("Lane", backref="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, lane={self.lane_id}, plate={self.raw_plate})>"
