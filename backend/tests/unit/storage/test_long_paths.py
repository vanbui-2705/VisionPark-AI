from uuid import uuid4

from app.core.config import Settings
from app.integrations.storage.local_storage import LocalStorageAdapter


def test_atomic_image_write_and_delete_support_long_workspace_paths(tmp_path):
    directory = tmp_path / ("a" * 80) / ("b" * 80)
    settings = Settings(_env_file=None, local_storage_path=str(directory))
    storage = LocalStorageAdapter(settings)
    lane_id = str(uuid4())
    data = b"\xff\xd8\xffsynthetic-jpeg-fixture"
    key = storage.save_image(data, lane_id)
    path = storage.base_dir / lane_id / key
    assert len(str(path)) > 260
    assert path.read_bytes() == data
    assert not path.with_suffix(path.suffix + ".tmp").exists()
    storage.delete_image(key, lane_id)
    assert not path.exists()
