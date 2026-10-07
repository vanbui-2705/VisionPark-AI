from alembic import command
from sqlalchemy import create_engine, inspect

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

    from sqlalchemy import MetaData, Table, Uuid
    from sqlalchemy.orm import Session

    from app.modules.alpr.models import Detection
    from app.modules.lanes.models import Lane

    config = make_alembic_config(database_url)
    command.upgrade(config, "aa276e942822")
    engine = create_engine(database_url)
    with Session(engine) as session:
        lane = Lane(name="existing-lane", direction="IN", video_source="demo.mp4", is_active=True)
        session.add(lane)
        session.flush()
        detection_id = uuid4()
        old_detections = Table("detections", MetaData(), autoload_with=engine)
        old_detections.c.id.type = Uuid()
        old_detections.c.lane_id.type = Uuid()
        session.execute(
            old_detections.insert().values(
                id=detection_id,
                lane_id=lane.id,
                image_key="existing.jpg",
                requires_confirmation=False,
                is_confirmed=False,
            )
        )
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
    import pytest

    with pytest.raises(RuntimeError, match="Refusing downgrade"):
        command.downgrade(config, "base")
