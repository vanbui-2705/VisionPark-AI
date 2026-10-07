"""Add audit_logs and missing detection columns

Revision ID: 20260930_audit
Revises: 20260930_parking
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260930_audit"
down_revision: str = "20260930_parking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("entity_type", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.String(length=100), nullable=False),
            sa.Column("old_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("audit_logs", schema=None) as batch_op:
            batch_op.create_index("ix_audit_logs_action", ["action"], unique=False)
            batch_op.create_index("ix_audit_logs_entity_id", ["entity_id"], unique=False)
            batch_op.create_index("ix_audit_logs_entity_type", ["entity_type"], unique=False)
    if "detections" in tables:
        det_cols = {c["name"] for c in inspector.get_columns("detections")}
        if "image_content_type" not in det_cols:
            op.add_column("detections", sa.Column("image_content_type", sa.String(length=50), nullable=False, server_default="image/jpeg"))
        if "image_size_bytes" not in det_cols:
            op.add_column("detections", sa.Column("image_size_bytes", sa.Integer(), nullable=True))
        if "requires_confirmation" not in det_cols:
            op.add_column("detections", sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.text("0" if dialect=="sqlite" else "false")))
        if "is_confirmed" not in det_cols:
            op.add_column("detections", sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("0" if dialect=="sqlite" else "false")))
        if "confirmed_plate" not in det_cols:
            op.add_column("detections", sa.Column("confirmed_plate", sa.String(length=50), nullable=True))
        if "confirmed_by_id" not in det_cols:
            op.add_column("detections", sa.Column("confirmed_by_id", sa.Uuid(), nullable=True))
            with op.batch_alter_table("detections", schema=None) as batch_op:
                batch_op.create_foreign_key("fk_detections_confirmed_by_id", "users", ["confirmed_by_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "detections" in tables:
        cols = {c["name"] for c in inspector.get_columns("detections")}
        if "confirmed_by_id" in cols:
            try:
                with op.batch_alter_table("detections", schema=None) as batch_op:
                    batch_op.drop_constraint("fk_detections_confirmed_by_id", type_="foreignkey")
            except Exception:
                pass
        for col in ["confirmed_by_id", "confirmed_plate", "is_confirmed", "requires_confirmation", "image_size_bytes", "image_content_type"]:
            if col in cols:
                with op.batch_alter_table("detections", schema=None) as batch_op:
                    batch_op.drop_column(col)
    if "audit_logs" in inspector.get_table_names():
        op.drop_table("audit_logs")
