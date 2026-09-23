from sqlalchemy import create_engine, inspect

from alembic import command
from tests.conftest import make_alembic_config


def test_migration_up_and_down_on_empty_database(database_url: str) -> None:
    config = make_alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert {"alembic_version", "roles", "users"}.issubset(inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(database_url)
    assert "roles" not in inspect(engine).get_table_names()
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()


def test_migration_head_matches_registered_models(database_url: str) -> None:
    config = make_alembic_config(database_url)
    command.upgrade(config, "head")
    command.check(config)


def test_upgrade_preserves_existing_detection(database_url: str) -> None:
    from uuid import uuid4

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.core.config import Settings
    from app.database.seed import seed_database
    from app.modules.alpr.models import Detection
    from app.modules.lanes.models import Lane

    config = make_alembic_config(database_url)
    command.upgrade(config, "aa276e942822")
    engine = create_engine(database_url)
    with Session(engine) as session:
        seed_database(session, Settings(_env_file=None, environment="test"))
        lane = session.scalar(select(Lane))
        detection_id = uuid4()
        session.add(Detection(id=detection_id, lane_id=lane.id, image_key="existing.jpg"))
        session.commit()
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = create_engine(database_url)
    with Session(engine) as session:
        record = session.get(Detection, detection_id)
        assert record.image_key == "existing.jpg"
        assert session.get(Lane, record.lane_id) is not None
    engine.dispose()
    command.downgrade(config, "base")
