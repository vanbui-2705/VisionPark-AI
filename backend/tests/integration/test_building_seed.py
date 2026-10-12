import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.database.seed_demo import seed_demo
from app.modules.buildings.models import Building, ParkingLot, UserBuilding
from app.modules.lanes.models import Lane
from app.modules.users.models import User
from tests.conftest import login


def test_two_building_demo_is_repeatable_and_does_not_reset_passwords(client, db_session):
    seed_demo(db_session, "first-demo-password")
    first = db_session.scalar(select(User).where(User.username == "demo_a_operator"))
    original_hash = first.password_hash
    seed_demo(db_session, "second-demo-password")
    db_session.refresh(first)
    assert first.password_hash == original_hash
    assert verify_password("first-demo-password", first.password_hash)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Building)
            .where(Building.code.in_(["DEMO_A", "DEMO_B"]))
        )
        == 2
    )
    assert db_session.scalar(select(func.count()).select_from(ParkingLot)) == 3
    assert (
        db_session.scalar(
            select(func.count()).select_from(UserBuilding).where(UserBuilding.user_id == first.id)
        )
        == 1
    )
    for code in ("a", "b"):
        token = login(client, f"demo_{code}_operator", "first-demo-password")["access_token"]
        response = client.get("/api/v1/lanes/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert {lane["name"] for lane in response.json()} == {
            f"DEMO_{code.upper()}_IN",
            f"DEMO_{code.upper()}_OUT",
        }


def test_demo_seed_rejects_collisions_and_short_password_without_commit(client, db_session):
    with pytest.raises(ValueError, match="12 characters"):
        seed_demo(db_session, "short")
    db_session.add(Lane(name="DEMO_B_IN", direction="IN", video_source="test"))
    db_session.commit()
    with pytest.raises(ValueError, match="another building"):
        seed_demo(db_session, "valid-demo-password")
    db_session.rollback()
    assert db_session.scalar(select(Building).where(Building.code == "DEMO_A")) is None


def test_one_command_bootstraps_two_buildings_from_empty_database(database_url):
    import os
    import subprocess
    import sys

    from tests.conftest import BACKEND_ROOT, TEST_JWT_SECRET

    environment = {
        **os.environ,
        "DATABASE_URL": database_url,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
        "AUTO_SEED": "false",
        "DEMO_SEED_PASSWORD": "disposable-fixture-password",
    }
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "app.database.seed_demo"],
            cwd=BACKEND_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Building)) == 3
        assert session.scalar(select(func.count()).select_from(User)) == 6
        assert session.scalar(select(func.count()).select_from(Lane)) == 4
        assert session.scalar(select(func.count()).select_from(UserBuilding)) == 6
    engine.dispose()
