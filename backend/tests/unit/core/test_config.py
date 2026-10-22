import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings


@pytest.mark.parametrize("password", [None, "", "short"])
def test_bootstrap_rejects_missing_or_short_admin_password(password):
    with pytest.raises(ValidationError, match="at least 8 characters"):
        Settings(_env_file=None, auto_seed=True, seed_admin_password=password)


@pytest.mark.parametrize("environment", ["development", "production"])
@pytest.mark.parametrize("secret", [DEV_JWT_SECRET, "replace-this-with-a-long-random-secret"])
def test_sample_signing_keys_are_rejected(environment, secret) -> None:
    with pytest.raises(ValidationError, match="sample or development signing key"):
        Settings(_env_file=None, environment=environment, jwt_secret_key=secret)


@pytest.mark.parametrize("environment", ["development", "production"])
@pytest.mark.parametrize(
    "variable,field", [("DATABASE_URL", "database_url"), ("JWT_SECRET_KEY", "jwt_secret_key")]
)
def test_required_environment_variables_have_no_fallback(monkeypatch, environment, variable, field):
    monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, environment=environment)
    assert any(
        item["loc"] == (field,) and item["type"] == "missing" for item in error.value.errors()
    )


@pytest.mark.parametrize("url", ["", "   ", "not-a-database-url"])
def test_invalid_database_url_is_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)


def test_cors_origins_are_parsed_and_trimmed() -> None:
    settings = Settings(cors_origins="http://one.test, http://two.test")
    assert settings.cors_origin_list == ["http://one.test", "http://two.test"]


def test_alembic_cli_reads_dotenv(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

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
