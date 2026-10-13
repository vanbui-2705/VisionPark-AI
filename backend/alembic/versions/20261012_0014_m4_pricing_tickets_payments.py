"""Add M4 pricing, ticket and payment storage.

Revision ID: 20261012_0014
Revises: 20261012_0013
"""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0014"
down_revision = "20261012_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_classes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "discount_percent BETWEEN 0 AND 100", name="ck_customer_classes_discount"
        ),
        sa.UniqueConstraint("building_id", "code"),
    )
    op.create_index("ix_customer_classes_building_id", "customer_classes", ["building_id"])
    op.create_table(
        "class_quotas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column(
            "customer_class_id",
            sa.Uuid(),
            sa.ForeignKey("customer_classes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vehicle_type", sa.String(40), nullable=False),
        sa.Column("max_active", sa.Integer(), nullable=False),
        sa.CheckConstraint("max_active >= 0", name="ck_class_quotas_max_active"),
        sa.UniqueConstraint("building_id", "customer_class_id", "vehicle_type"),
    )
    op.create_index("ix_class_quotas_building_id", "class_quotas", ["building_id"])
    op.create_table(
        "ticket_products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("vehicle_type", sa.String(40), nullable=False),
        sa.Column(
            "customer_class_id",
            sa.Uuid(),
            sa.ForeignKey("customer_classes.id", ondelete="RESTRICT"),
        ),
        sa.Column("requires_vehicle", sa.Boolean(), nullable=False),
        sa.Column("sale_limit", sa.Integer()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('HOURLY', 'DAILY', 'MONTHLY', 'NIGHT')", name="ck_ticket_products_kind"
        ),
        sa.CheckConstraint(
            "sale_limit IS NULL OR sale_limit >= 0", name="ck_ticket_products_sale_limit"
        ),
        sa.UniqueConstraint("building_id", "code"),
    )
    op.create_index("ix_ticket_products_building_id", "ticket_products", ["building_id"])
    op.create_table(
        "pricing_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.CheckConstraint("version_number > 0", name="ck_pricing_versions_number"),
        sa.UniqueConstraint("building_id", "version_number"),
    )
    op.create_index("ix_pricing_versions_building_id", "pricing_versions", ["building_id"])
    op.create_table(
        "pricing_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("pricing_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vehicle_type", sa.String(40), nullable=False),
        sa.Column("ticket_kind", sa.String(20), nullable=False),
        sa.Column(
            "customer_class_id",
            sa.Uuid(),
            sa.ForeignKey("customer_classes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rule_data", sa.JSON(), nullable=False),
        sa.UniqueConstraint("version_id", "vehicle_type", "ticket_kind", "customer_class_id"),
    )
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_plate", sa.String(50)),
        sa.Column("ticket_code", sa.String(80)),
        sa.Column("vehicle_type", sa.String(40), nullable=False),
        sa.Column(
            "customer_class_id",
            sa.Uuid(),
            sa.ForeignKey("customer_classes.id", ondelete="RESTRICT"),
        ),
        sa.UniqueConstraint("building_id", "normalized_plate"),
        sa.UniqueConstraint("building_id", "ticket_code"),
        sa.CheckConstraint(
            "normalized_plate IS NOT NULL OR ticket_code IS NOT NULL",
            name="ck_vehicles_identifier",
        ),
    )
    op.create_index("ix_vehicles_building_id", "vehicles", ["building_id"])
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("ticket_products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Uuid(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grace_days", sa.Integer(), nullable=False),
        sa.CheckConstraint("valid_until >= valid_from", name="ck_subscriptions_validity"),
        sa.CheckConstraint("grace_days >= 0", name="ck_subscriptions_grace"),
    )
    op.create_index(
        "ix_subscriptions_building_vehicle", "subscriptions", ["building_id", "vehicle_id"]
    )
    op.create_table(
        "guest_invites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column(
            "resident_vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="RESTRICT")
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("free_minutes", sa.Integer(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("valid_until >= valid_from", name="ck_guest_invites_validity"),
        sa.CheckConstraint("free_minutes >= 0", name="ck_guest_invites_free_minutes"),
        sa.UniqueConstraint("building_id", "code"),
    )
    op.create_index("ix_guest_invites_building_id", "guest_invites", ["building_id"])
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("parking_transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "price_version_id",
            sa.Uuid(),
            sa.ForeignKey("pricing_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lost_ticket", sa.Boolean(), nullable=False),
        sa.Column("overtime", sa.Boolean(), nullable=False),
        sa.Column("extra_free_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "guest_invite_id", sa.Uuid(), sa.ForeignKey("guest_invites.id", ondelete="RESTRICT")
        ),
        sa.Column("total_vnd", sa.Integer(), nullable=False),
        sa.Column("lines", sa.JSON(), nullable=False),
        sa.CheckConstraint("total_vnd >= 0", name="ck_invoices_total"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_invoices_building_id", "invoices", ["building_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider_ref", sa.String(120)),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount_vnd", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("provider_amount_vnd", sa.Integer()),
        sa.Column("provider_status", sa.String(20)),
        sa.CheckConstraint("amount_vnd >= 0", name="ck_payments_amount"),
        sa.CheckConstraint(
            "status IN ('PENDING','PROCESSING','PAID','FAILED','REFUNDED')",
            name="ck_payments_status",
        ),
        sa.UniqueConstraint("provider_ref"),
        sa.UniqueConstraint("invoice_id", "idempotency_key"),
    )
    op.create_index("ix_payments_building_id", "payments", ["building_id"])
    op.add_column("parking_transactions", sa.Column("price_snapshot", sa.JSON()))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM payments")).scalar():
        raise RuntimeError("Refusing downgrade: payment records would be lost")
    if bind.execute(sa.text("SELECT COUNT(*) FROM invoices")).scalar():
        raise RuntimeError("Refusing downgrade: invoice records would be lost")
    if bind.execute(
        sa.text("SELECT COUNT(*) FROM parking_transactions WHERE price_snapshot IS NOT NULL")
    ).scalar():
        raise RuntimeError("Refusing downgrade: price snapshots would be lost")
    op.drop_column("parking_transactions", "price_snapshot")
    for name in (
        "payments",
        "invoices",
        "guest_invites",
        "subscriptions",
        "vehicles",
        "pricing_rules",
        "pricing_versions",
        "ticket_products",
        "class_quotas",
        "customer_classes",
    ):
        op.drop_table(name)
