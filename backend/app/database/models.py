"""Alembic model import registry.

Domain owners add their model imports here so Alembic can discover metadata without placing
business models inside the database package.
"""

from app.modules.users.models import Role, User
from app.modules.lanes.models import Lane
from app.modules.alpr.models import Detection

__all__ = ["Role", "User", "Lane", "Detection"]
