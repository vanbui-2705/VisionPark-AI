from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.database.session import database
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName


def seed_database(session: Session, settings: Settings) -> None:
    """Provision roles and an administrator only; never overwrite existing identities."""

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
    for username, display_name, password, role_name in demo_users[:1]:
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
