"""Audit Logs model - Ghi vết thao tác người dùng."""
from sqlalchemy import Column, String, ForeignKey, JSON, Uuid
from sqlalchemy.orm import relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)      # VD: CONFIRM_PLATE, CREATE_LANE
    entity_type = Column(String(100), nullable=False, index=True) # VD: Detection, Lane
    entity_id = Column(String(100), nullable=False, index=True)   # ID của dòng dữ liệu bị tác động
    
    # Lưu trữ dữ liệu trước và sau khi sửa (dạng JSON)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog(action={self.action}, entity={self.entity_type})>"