from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.database.session import database
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName
from app.modules.lanes.models import Lane


def seed_database(session: Session, settings: Settings) -> None:
    """Create the Phase 1 roles and demo users without duplicating existing rows."""

    # ===== SEED ROLES =====
    roles: dict[RoleName, Role] = {}
    for role_name in RoleName:
        role = session.scalar(select(Role).where(Role.name == role_name.value))
        if role is None:
            role = Role(name=role_name.value)
            session.add(role)
            session.flush()
        roles[role_name] = role

    # ===== SEED USERS =====
    demo_users = (
        (
            settings.seed_admin_username,
            "VisionPark Administrator",
            settings.seed_admin_password,
            RoleName.ADMIN,
        ),
        (
            settings.seed_operator_username,
            "VisionPark Operator",
            settings.seed_operator_password,
            RoleName.OPERATOR,
        ),
    )
    for username, display_name, password, role_name in demo_users:
        if password is None:
            continue
        normalized_username = username.strip().lower()
        existing = session.scalar(select(User).where(User.username == normalized_username))
        if existing is None:
            session.add(
                User(
                    username=normalized_username,
                    display_name=display_name,
                    password_hash=hash_password(password.get_secret_value()),
                    role=roles[role_name],
                    is_active=True,
                )
            )

    # ===== SEED LANES (Idempotent) =====
    demo_lanes = [
        {
            "name": "LANE_IN_01",
            "direction": "IN",
            "video_source": "rtsp://demo/in",
            "is_active": True,
        },
        {
            "name": "LANE_OUT_01",
            "direction": "OUT",
            "video_source": "rtsp://demo/out",
            "is_active": True,
        },
    ]

    for lane_data in demo_lanes:
        existing = session.scalar(select(Lane).where(Lane.name == lane_data["name"]))
        if existing is None:
            session.add(Lane(**lane_data))

    session.commit()


def main() -> None:
    settings = get_settings()
    database.configure(settings.database_url, echo=settings.database_echo)
    try:
        with database.create_session() as session:
            seed_database(session, settings)
    finally:
        database.dispose()


if __name__ == "__main__":
    main()