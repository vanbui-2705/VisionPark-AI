from app.core.config import get_settings
from app.integrations.storage.local_storage import LocalStorageAdapter


# Factory function để tạo instance với settings đúng
def get_storage_adapter():
    """Create and return a LocalStorageAdapter instance with proper settings."""
    return LocalStorageAdapter(get_settings())


__all__ = ["LocalStorageAdapter", "get_storage_adapter"]
