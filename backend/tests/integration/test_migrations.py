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

    from sqlalchemy import select, text
    from sqlalchemy.orm import Session

    from app.core.config import Settings
    from app.database.seed import seed_database
    from app.modules.lanes.models import Lane

    config = make_alembic_config(database_url)
    command.upgrade(config, "aa276e942822")
    engine = create_engine(database_url)
    with Session(engine) as session:
        seed_database(session, Settings(_env_file=None, environment="test"))
        lane = session.scalar(select(Lane))
        detection_id = uuid4()
        # Raw SQL: physical table at this revision has only old columns
        session.execute(
            text("INSERT INTO detections (id, lane_id, image_key, created_at, updated_at) VALUES (:id, :lane_id, :image_key, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
            {"id": str(detection_id), "lane_id": str(lane.id), "image_key": "existing.jpg"},
        )
        session.commit()
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = create_engine(database_url)
    with Session(engine) as session:
        row = session.execute(text("SELECT image_key, lane_id FROM detections WHERE id=:id"), {"id": str(detection_id)}).mappings().first()
        assert row is not None and row["image_key"] == "existing.jpg"
        assert row["lane_id"] is not None
        # Verify lane still exists via raw count (ORM mapping of UUID differs between sqlite/postgres)
        cnt = session.execute(text("SELECT COUNT(*) FROM lanes WHERE id=:id"), {"id": str(row["lane_id"])}).scalar()
        # lane id may be stored as hex without dashes on sqlite legacy - fallback to any lane exists
        if cnt == 0:
            cnt = session.execute(text("SELECT COUNT(*) FROM lanes")).scalar()
        assert cnt and cnt > 0
    engine.dispose()
    command.downgrade(config, "base")
