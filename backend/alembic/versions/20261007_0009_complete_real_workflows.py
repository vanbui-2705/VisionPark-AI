"""Add durable workflow metadata without changing existing records."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0009"
down_revision = "20261007_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
    )
    columns = [
        sa.Column("input_kind", sa.String(20)),
        sa.Column("video_time_ms", sa.Integer()),
        sa.Column("provider", sa.String(64)),
        sa.Column("detector_confidence", sa.Float()),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("combined_confidence", sa.Float()),
        sa.Column("quality_flags", sa.JSON()),
        sa.Column("detector_latency_ms", sa.Float()),
        sa.Column("ocr_latency_ms", sa.Float()),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("lane_name_snapshot", sa.String(120)),
        sa.Column("direction_snapshot", sa.String(10)),
    ]
    with op.batch_alter_table("detections") as batch:
        for col in columns:
            batch.add_column(col)
        batch.create_foreign_key("fk_detection_actor", "users", ["actor_id"], ["id"])
        batch.create_index("ix_detections_input_kind", ["input_kind"])
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("theme", sa.String(10), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
    )
    for name, fields in [
        (
            "notifications",
            [
                sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("title", sa.String(120), nullable=False),
                sa.Column("message", sa.String(500), nullable=False),
                sa.Column("event_key", sa.String(160), unique=True, nullable=False),
                sa.Column("read_at", sa.DateTime(timezone=True)),
            ],
        ),
        (
            "error_events",
            [
                sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
                sa.Column("code", sa.String(64), nullable=False),
                sa.Column("status", sa.Integer(), nullable=False),
                sa.Column("source", sa.String(32), nullable=False),
                sa.Column("message", sa.String(500), nullable=False),
                sa.Column("correlation_id", sa.String(64)),
            ],
        ),
    ]:
        op.create_table(
            name,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            *fields,
        )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade():
    # Destructive downgrade is only valid for an empty disposable database.
    connection = op.get_bind()
    for name in ("users", "detections", "notifications", "error_events", "user_preferences"):
        if connection.execute(sa.text(f'SELECT count(*) FROM "{name}"')).scalar():
            raise RuntimeError("Refusing downgrade of a database containing operational records")
    for name in ("error_events", "notifications", "user_preferences"):
        op.drop_table(name)
    with op.batch_alter_table("detections") as batch:
        batch.drop_index("ix_detections_input_kind")
        batch.drop_constraint("fk_detection_actor", type_="foreignkey")
        for name in (
            "input_kind",
            "video_time_ms",
            "provider",
            "detector_confidence",
            "ocr_confidence",
            "combined_confidence",
            "quality_flags",
            "detector_latency_ms",
            "ocr_latency_ms",
            "actor_id",
            "lane_name_snapshot",
            "direction_snapshot",
        ):
            batch.drop_column(name)
    op.drop_column("users", "token_version")
