"""Backfill detection metadata and audit log tables for Phase 1."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0004"
down_revision: str | None = "20260921_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    existing = _columns("detections")
    additions = [
        sa.Column(
            "image_content_type", sa.String(length=50), nullable=False, server_default="image/jpeg"
        ),
        sa.Column("image_size_bytes", sa.Integer(), nullable=True),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed_plate", sa.String(length=50), nullable=True),
        sa.Column("confirmed_by_id", sa.Uuid(), nullable=True),
    ]
    for column in additions:
        if column.name not in existing:
            op.add_column("detections", column)
    if "confirmed_by_id" not in existing:
        with op.batch_alter_table("detections") as batch:
            batch.create_foreign_key(
                "fk_detections_confirmed_by_id_users",
                "users",
                ["confirmed_by_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(op.get_bind())
    if "audit_logs" not in inspector.get_table_names():
        op.create_table(
            "audit_logs",
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("entity_type", sa.String(length=100), nullable=False),
            sa.Column("entity_id", sa.String(length=100), nullable=False),
            sa.Column("old_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
        op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "audit_logs" in inspector.get_table_names():
        op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
        op.drop_index("ix_audit_logs_action", table_name="audit_logs")
        op.drop_table("audit_logs")
    existing = _columns("detections")
    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys("detections")
    }
    if "fk_detections_confirmed_by_id_users" in foreign_keys:
        with op.batch_alter_table("detections") as batch:
            batch.drop_constraint("fk_detections_confirmed_by_id_users", type_="foreignkey")
    for name in (
        "confirmed_by_id",
        "confirmed_plate",
        "is_confirmed",
        "requires_confirmation",
        "image_size_bytes",
        "image_content_type",
    ):
        if name in existing:
            with op.batch_alter_table("detections") as batch:
                batch.drop_column(name)
