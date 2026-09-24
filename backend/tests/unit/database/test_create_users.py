import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.database.base import Base
from app.database.create_users import create_user
from app.modules.users.models import User
from app.modules.users.schemas import RoleName


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def test_create_user_normalizes_username_and_assigns_role(session: Session) -> None:
    user = create_user(
        session,
        username="  Accountant.One  ",
        display_name="Accountant One",
        password="safe-password",
        role_name=RoleName.ACCOUNTANT,
    )
    session.commit()

    stored = session.get(User, user.id)
    assert stored is not None
    assert stored.username == "accountant.one"
    assert stored.role.name == RoleName.ACCOUNTANT.value
    assert stored.is_active
    assert verify_password("safe-password", stored.password_hash)


def test_create_user_rejects_duplicate_username(session: Session) -> None:
    create_user(
        session,
        username="operator.two",
        display_name="Operator Two",
        password="safe-password",
        role_name=RoleName.OPERATOR,
    )
    session.commit()

    with pytest.raises(ValueError, match="already exists"):
        create_user(
            session,
            username="OPERATOR.TWO",
            display_name="Another Operator",
            password="another-password",
            role_name=RoleName.OPERATOR,
        )


@pytest.mark.parametrize(
    ("username", "display_name", "password", "message"),
    [
        ("invalid user", "Valid Name", "safe-password", "Username may contain"),
        ("valid-user", "", "safe-password", "Display name must contain"),
        ("valid-user", "Valid Name", "short", "at least 8"),
    ],
)
def test_create_user_validates_input(
    session: Session,
    username: str,
    display_name: str,
    password: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        create_user(
            session,
            username=username,
            display_name=display_name,
            password=password,
            role_name=RoleName.TECHNICIAN,
        )
