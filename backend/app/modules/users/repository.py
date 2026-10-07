from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.users.models import Role, User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username.strip().lower())
        return self.session.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def list(self, q: str | None, role: str | None, active: bool | None) -> list[User]:
        statement = select(User).order_by(User.created_at.desc()).limit(200)
        if q:
            statement = statement.where(
                or_(User.username.ilike(f"%{q}%"), User.display_name.ilike(f"%{q}%"))
            )
        if role:
            statement = statement.join(User.role).where(Role.name == role)
        if active is not None:
            statement = statement.where(User.is_active == active)
        return list(self.session.scalars(statement).unique())

    def get_role(self, name: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.name == name))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))
