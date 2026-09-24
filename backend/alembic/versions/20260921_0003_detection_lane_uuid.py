"""Normalize legacy SQLite detection lane IDs to UUID storage.

PostgreSQL uses UUID in the corrected parent revision: the original parent
could never create a varchar -> uuid foreign key there. Existing SQLite databases
at aa276e942822 are upgraded in place; no migration stamp or data reset is needed.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260921_0003"
down_revision = "aa276e942822"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("UPDATE detections SET lane_id = replace(lane_id, '-', '')")
        with op.batch_alter_table("detections") as batch:
            batch.alter_column(
                "lane_id", existing_type=sa.String(50), type_=sa.Uuid(), existing_nullable=False
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("detections") as batch:
            batch.alter_column(
                "lane_id", existing_type=sa.Uuid(), type_=sa.String(50), existing_nullable=False
            )
