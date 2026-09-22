import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings


def test_production_rejects_development_secret() -> None:
    with pytest.raises(ValidationError, match="Production must provide"):
        Settings(environment="production", jwt_secret_key=DEV_JWT_SECRET)


def test_cors_origins_are_parsed_and_trimmed() -> None:
    settings = Settings(cors_origins="http://one.test, http://two.test")
    assert settings.cors_origin_list == ["http://one.test", "http://two.test"]


def test_alembic_cli_reads_dotenv(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    from alembic import command

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    url = f"sqlite:///{(tmp_path / 'from-env.db').as_posix()}"
    (tmp_path / ".env").write_text(f"DATABASE_URL={url}\n", encoding="utf-8")
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert "detections" in inspect(engine).get_table_names()
    engine.dispose()
