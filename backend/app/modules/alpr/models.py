"""ALPR Detection model - lưu lịch sử nhận diện biển số."""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Detection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Bảng lưu lịch sử nhận diện biển số xe."""
    
    __tablename__ = "detections"
    
    # Foreign key đến Lane
    lane_id = Column(Uuid, 
        ForeignKey("lanes.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Thông tin ảnh & Media Metadata (VỪA THÊM)
    image_key = Column(String(255), nullable=False, index=True, 
        comment="Storage key do ImageStorage trả về")
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

    # 4. Thông tin Xác nhận / Confirmation
    requires_confirmation = Column(Boolean, default=False, nullable=False)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_plate = Column(String(50), nullable=True)
    confirmed_by_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationship
    lane = relationship("Lane", backref="detections")
    
    def __repr__(self):
        return f"<Detection(id={self.id}, lane={self.lane_id}, plate={self.raw_plate})>"