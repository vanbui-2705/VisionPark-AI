"""Resolve media paths, including long absolute paths on Windows."""

import os
from pathlib import Path


def media_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    path = str(root)
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return root
    if path.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + path[2:])
    return Path("\\\\?\\" + path)
