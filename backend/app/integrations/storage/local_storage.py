from pathlib import Path
from uuid import uuid4

from app.alpr.ports.image_storage import ImageStorage
from app.core.config import Settings, get_settings


class LocalStorageAdapter(ImageStorage):
    """Local filesystem storage implementation for ALPR images."""

    VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_dir = Path(self.settings.local_storage_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_extension(self, file_bytes: bytes, suggested_ext: str) -> str:
        """Validate and normalize file extension from magic bytes."""
        # Detect actual extension from file header
        if file_bytes[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        else:
            # Fallback to suggested extension if it's valid
            ext = f".{suggested_ext.lstrip('.')}"

        if ext.lower() not in self.VALID_EXTENSIONS:
            ext = ".jpg"  # Default to jpg for unknown types

        return ext

    def save_image(self, image_bytes: bytes, lane_id: str) -> str:
        """
        Lưu ảnh vào local filesystem và trả về storage key.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG)
            lane_id: Lane identifier for organizing files

        Returns:
            Storage key (unique filename) for later retrieval
        """
        # Generate unique key: {lane_id}_{uuid}.{ext}
        ext = self._validate_extension(image_bytes, "jpg")
        unique_id = uuid4().hex
        key = f"{lane_id}_{unique_id}{ext}"

        # Create lane-specific subdirectory
        lane_dir = self.base_dir / lane_id
        lane_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = lane_dir / key
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return key

    def delete_image(self, image_key: str, lane_id: str) -> None:
        (self.base_dir / lane_id / image_key).unlink(missing_ok=True)
