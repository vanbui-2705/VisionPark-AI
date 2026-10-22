"""Shared building ownership and the one-building/one-parking-lot foundation."""

from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

DEFAULT_BUILDING_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_BUILDING_SQL = "00000000000000000000000000000001"


class BuildingOwnedMixin:
    # Keep previous application writes valid during rollout. Tenant-aware services
    # must explicitly supply the building resolved from the authenticated account.
    building_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=False,
        default=lambda: DEFAULT_BUILDING_ID,
        server_default=DEFAULT_BUILDING_SQL,
        index=True,
    )


class Building(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "buildings"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Ho_Chi_Minh", server_default="Asia/Ho_Chi_Minh"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ParkingLot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parking_lots"

    building_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    settings_revision: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    __mapper_args__ = {"version_id_col": settings_revision, "version_id_generator": False}


class UserBuilding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_buildings"
    __table_args__ = (
        UniqueConstraint("user_id", "building_id", name="uq_user_buildings_membership"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    building_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("buildings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
