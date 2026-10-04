"""Merge the Phase 1 and parking transaction migration branches."""

from collections.abc import Sequence

revision: str = "20261004_0005"
down_revision: tuple[str, str] = ("20260929_0004", "20261002_0004")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge both existing migration branches without changing the schema."""


def downgrade() -> None:
    """Split the migration graph back into its two parent branches."""
