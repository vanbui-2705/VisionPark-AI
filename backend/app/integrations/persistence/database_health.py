"""Compatibility import for the shared database readiness dependency."""

from app.database.session import get_database_readiness

__all__ = ["get_database_readiness"]
