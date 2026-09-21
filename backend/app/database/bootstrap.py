"""Migrate the configured database, then optionally seed local demo accounts."""

from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import Settings
from app.database.seed import seed_database
from app.database.session import DatabaseManager


def main() -> None:
    settings = Settings()
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")
    if settings.auto_seed:
        database = DatabaseManager()
        database.configure(settings.database_url)
        try:
            with database.create_session() as session:
                seed_database(session, settings)
        finally:
            database.dispose()


if __name__ == "__main__":
    main()
