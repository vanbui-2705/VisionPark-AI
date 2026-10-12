"""Persistent M4 ticket, pricing, invoice and payment records."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CustomerClass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customer_classes"
    __table_args__ = (
        CheckConstraint("discount_percent BETWEEN 0 AND 100", name="ck_customer_classes_discount"),
        UniqueConstraint("building_id", "code"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClassQuota(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "class_quotas"
    __table_args__ = (
        CheckConstraint("max_active >= 0", name="ck_class_quotas_max_active"),
        UniqueConstraint("building_id", "customer_class_id", "vehicle_type"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    customer_class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_classes.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    max_active: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ticket_products"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('HOURLY', 'DAILY', 'MONTHLY', 'NIGHT')", name="ck_ticket_products_kind"
        ),
        CheckConstraint(
            "sale_limit IS NULL OR sale_limit >= 0", name="ck_ticket_products_sale_limit"
        ),
        UniqueConstraint("building_id", "code"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_class_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_classes.id", ondelete="RESTRICT")
    )
    requires_vehicle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sale_limit: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PricingVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pricing_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_pricing_versions_number"),
        UniqueConstraint("building_id", "version_number"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class PricingRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        UniqueConstraint("version_id", "vehicle_type", "ticket_kind", "customer_class_id"),
    )

    version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pricing_versions.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    ticket_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_class_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_classes.id", ondelete="RESTRICT"), nullable=False
    )
    rule_data: Mapped[dict] = mapped_column(JSON, nullable=False)


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint(
            "normalized_plate IS NOT NULL OR ticket_code IS NOT NULL", name="ck_vehicles_identifier"
        ),
        UniqueConstraint("building_id", "normalized_plate"),
        UniqueConstraint("building_id", "ticket_code"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    normalized_plate: Mapped[str | None] = mapped_column(String(50))
    ticket_code: Mapped[str | None] = mapped_column(String(80))
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_class_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_classes.id", ondelete="RESTRICT")
    )


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("valid_until >= valid_from", name="ck_subscriptions_validity"),
        CheckConstraint("grace_days >= 0", name="ck_subscriptions_grace"),
        Index("ix_subscriptions_building_vehicle", "building_id", "vehicle_id"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ticket_products.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    zone_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


class GuestInvite(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "guest_invites"
    __table_args__ = (
        CheckConstraint("valid_until >= valid_from", name="ck_guest_invites_validity"),
        CheckConstraint("free_minutes >= 0", name="ck_guest_invites_free_minutes"),
        UniqueConstraint("building_id", "code"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    resident_vehicle_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT")
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    free_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("total_vnd >= 0", name="ck_invoices_total"),
        UniqueConstraint("transaction_id"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parking_transactions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    price_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pricing_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    check_out_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lost_ticket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extra_free_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    guest_invite_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("guest_invites.id", ondelete="RESTRICT")
    )
    total_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    lines: Mapped[list] = mapped_column(JSON, nullable=False)


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_vnd >= 0", name="ck_payments_amount"),
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','PAID','FAILED','REFUNDED')",
            name="ck_payments_status",
        ),
        UniqueConstraint("provider_ref"),
        UniqueConstraint("invoice_id", "idempotency_key"),
    )

    building_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False
    )
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    amount_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_amount_vnd: Mapped[int | None] = mapped_column(Integer)
    provider_status: Mapped[str | None] = mapped_column(String(20))
