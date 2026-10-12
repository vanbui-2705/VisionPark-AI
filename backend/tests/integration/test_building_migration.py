from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, Uuid, create_engine, inspect, select

from app.modules.buildings.models import DEFAULT_BUILDING_ID
from tests.conftest import make_alembic_config

PARENT = "b9c0f377213e"


def reflected_table(engine, name):
    table = Table(name, MetaData(), autoload_with=engine)
    for column in table.c:
        if column.name != "entity_id" and (column.name == "id" or column.name.endswith("_id")):
            column.type = Uuid()
    return table


def test_foundation_backfills_and_rollback_preserves_legacy_data(database_url):
    config = make_alembic_config(database_url)
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    command.upgrade(config, PARENT)
    engine = create_engine(database_url)
    role_id, user_id, lane_id, detection_id, transaction_id, audit_id = [uuid4() for _ in range(6)]
    legacy = {
        "roles": dict(id=role_id, name="OPERATOR"),
        "users": dict(
            id=user_id,
            username="legacy",
            display_name="Legacy",
            role_id=role_id,
            password_hash="preserve-exact-hash",
            is_active=True,
        ),
        "lanes": dict(
            id=lane_id, name="legacy-in", direction="IN", video_source="legacy.mp4", is_active=True
        ),
        "detections": dict(
            id=detection_id,
            lane_id=lane_id,
            image_key="legacy.jpg",
            image_content_type="image/jpeg",
            requires_confirmation=False,
            is_confirmed=False,
        ),
        "parking_transactions": dict(
            id=transaction_id,
            lane_id=lane_id,
            detection_id=detection_id,
            license_plate="TEST123",
            normalized_plate="TEST123",
            status="PARKED",
            source="MANUAL_ENTRY",
            idempotency_key="old",
            request_fingerprint="a" * 64,
            is_manual_override=False,
        ),
        "audit_logs": dict(
            id=audit_id,
            user_id=user_id,
            action="CREATE_CHECKIN",
            entity_type="ParkingTransaction",
            entity_id=str(transaction_id),
            old_value=None,
            new_value={"plate": "TEST123"},
        ),
        "notifications": dict(
            id=uuid4(),
            user_id=user_id,
            title="Legacy",
            message="Preserve",
            event_key="legacy-notification",
        ),
        "error_events": dict(
            id=uuid4(), user_id=user_id, code="TEST", status=400, source="test", message="Preserve"
        ),
    }
    with engine.begin() as connection:
        for name, values in legacy.items():
            connection.execute(reflected_table(engine, name).insert().values(**values))
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        for name, values in legacy.items():
            table = reflected_table(engine, name)
            row = connection.execute(select(table).where(table.c.id == values["id"]))
            record = row.mappings().one()
            for key, value in values.items():
                assert record[key] == value
            if "building_id" in table.c:
                assert record["building_id"] == DEFAULT_BUILDING_ID
                assert not next(
                    c for c in inspect(engine).get_columns(name) if c["name"] == "building_id"
                )["nullable"]
        memberships = reflected_table(engine, "user_buildings")
        assert connection.execute(select(memberships.c.user_id)).scalar_one() == user_id
        lots = reflected_table(engine, "parking_lots")
        assert connection.execute(select(lots.c.building_id)).scalar_one() == DEFAULT_BUILDING_ID
    engine.dispose()
    command.downgrade(config, PARENT)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        for name, values in legacy.items():
            table = reflected_table(engine, name)
            record = (
                connection.execute(select(table).where(table.c.id == values["id"])).mappings().one()
            )
            for key, value in values.items():
                assert record[key] == value
        assert "buildings" not in inspect(engine).get_table_names()
    engine.dispose()
    command.upgrade(config, "head")


def test_foundation_downgrade_refuses_to_erase_tenant_isolation(migrated_database_url):
    engine = create_engine(migrated_database_url)
    with engine.begin() as connection:
        connection.execute(
            reflected_table(engine, "buildings")
            .insert()
            .values(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                code="SECOND",
                name="Second",
            )
        )
    engine.dispose()
    with pytest.raises(RuntimeError, match="non-default buildings"):
        command.downgrade(make_alembic_config(migrated_database_url), PARENT)
