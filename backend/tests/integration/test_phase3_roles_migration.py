from uuid import uuid4

from alembic import command
from sqlalchemy import create_engine, select

from tests.conftest import make_alembic_config
from tests.integration.test_building_migration import reflected_table


def test_role_mapping_upgrade_and_downgrade_preserve_user_identity(database_url):
    config = make_alembic_config(database_url)
    command.upgrade(config, "20261012_0012")
    engine = create_engine(database_url)
    roles = reflected_table(engine, "roles")
    users = reflected_table(engine, "users")
    role_ids = {name: uuid4() for name in ("ADMIN", "TECHNICIAN", "OPERATOR", "ACCOUNTANT")}
    user_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            roles.insert(), [{"id": ident, "name": name} for name, ident in role_ids.items()]
        )
        conn.execute(
            users.insert().values(
                id=user_id,
                username="legacy-admin",
                display_name="Legacy",
                password_hash="exact-legacy-hash",
                role_id=role_ids["ADMIN"],
                is_active=True,
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        upgraded = reflected_table(engine, "users")
        user = conn.execute(select(upgraded).where(upgraded.c.id == user_id)).mappings().one()
        assert user["password_hash"] == "exact-legacy-hash" and user["role_id"] == role_ids["ADMIN"]
        assert user["must_change_password"] is False
        renamed = dict(conn.execute(select(roles.c.name, roles.c.id)).all())
        assert renamed == {
            "SYSTEM_ADMIN": role_ids["ADMIN"],
            "BUILDING_ADMIN": role_ids["TECHNICIAN"],
            "OPERATOR": role_ids["OPERATOR"],
            "ACCOUNTANT": role_ids["ACCOUNTANT"],
        }
    engine.dispose()
    command.downgrade(config, "20261012_0012")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        assert dict(conn.execute(select(roles.c.name, roles.c.id)).all()) == role_ids
        assert (
            conn.execute(select(users.c.password_hash).where(users.c.id == user_id)).scalar_one()
            == "exact-legacy-hash"
        )
    engine.dispose()
