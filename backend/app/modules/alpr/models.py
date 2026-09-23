"""ALPR Detection model - lưu lịch sử nhận diện biển số."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Detection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Bảng lưu lịch sử nhận diện biển số xe."""

    __tablename__ = "detections"

    # Foreign key đến Lane
    lane_id = Column(Uuid(), ForeignKey("lanes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Thông tin ảnh đã lưu
    image_key = Column(
        String(255), nullable=False, index=True, comment="Storage key do ImageStorage trả về"
    )

    # Dữ liệu biển số
    raw_plate = Column(String(50), nullable=True, index=True)
    normalized_plate = Column(String(50), nullable=True, index=True)

    # Bounding box coordinates
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)

    # Metrics
    confidence = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Relationship
    lane = relationship("Lane", backref="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, lane={self.lane_id}, plate={self.raw_plate})>"
