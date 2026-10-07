"""Read-only media/reference audit. Reports missing and orphan files without deleting anything."""

import json
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import database
from app.modules.alpr.models import Detection


def main():
    settings = get_settings()
    database.configure(settings.database_url)
    root = Path(settings.local_storage_path).resolve()
    with database.create_session() as session:
        referenced = {
            f"{row.lane_id}/{row.image_key}"
            for row in session.scalars(select(Detection))
            if row.image_key
        }
    files = {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()}
    print(
        json.dumps(
            {
                "referenced": len(referenced),
                "files": len(files),
                "missing": sorted(referenced - files),
                "orphan": sorted(files - referenced),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
