"""Explicit, repeatable two-building fixtures; never run automatically at startup."""

import os
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.database.bootstrap import main as bootstrap
from app.database.session import DatabaseManager
from app.modules.buildings.models import Building, ParkingLot, UserBuilding
from app.modules.lanes.models import Lane
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName


def seed_demo(session: Session, password: str) -> None:
    if len(password) < 12:
        raise ValueError("DEMO_SEED_PASSWORD must contain at least 12 characters")
    for code in ("DEMO_A", "DEMO_B"):
        building_id = uuid5(NAMESPACE_URL, f"visionpark:demo-building:{code}")
        building = session.get(Building, building_id)
        if building is None:
            building = Building(id=building_id, code=code, name=f"Demo building {code[-1]}")
            session.add(building)
            session.flush()
            session.add(ParkingLot(building_id=building_id))
        for direction in ("IN", "OUT"):
            name = f"{code}_{direction}"
            lane = session.scalar(select(Lane).where(Lane.name == name))
            if lane is None:
                session.add(
                    Lane(
                        name=name,
                        direction=direction,
                        building_id=building_id,
                        video_source=f"fixture://phase-3/{code.lower()}/{direction.lower()}.mp4",
                    )
                )
            elif lane.building_id != building_id:
                raise ValueError(f"Existing lane {name} belongs to another building")
        for role_name in (RoleName.OPERATOR, RoleName.ACCOUNTANT):
            username = f"{code.lower()}_{role_name.value.lower()}"
            role = session.scalar(select(Role).where(Role.name == role_name.value))
            if role is None:
                role = Role(name=role_name.value)
                session.add(role)
                session.flush()
            user = session.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    display_name=f"Demo {code} {role_name.value}",
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
                session.add(user)
                session.flush()
                session.add(UserBuilding(user_id=user.id, building_id=building_id))
            else:
                memberships = list(
                    session.scalars(
                        select(UserBuilding.building_id).where(UserBuilding.user_id == user.id)
                    )
                )
                if memberships != [building_id] or user.role_id != role.id:
                    raise ValueError(f"Existing user {username} does not match the demo fixture")
    session.commit()


def main() -> None:
    password = os.environ.get("DEMO_SEED_PASSWORD", "")
    if len(password) < 12:
        raise ValueError("Set DEMO_SEED_PASSWORD (at least 12 characters) before seeding")
    # One command works on an empty disposable database, with a single Alembic head.
    bootstrap()
    settings = Settings()
    manager = DatabaseManager()
    manager.configure(settings.database_url)
    try:
        with manager.create_session() as session:
            seed_demo(session, password)
    finally:
        manager.dispose()


if __name__ == "__main__":
    main()
