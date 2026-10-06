from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import RoleName

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise AppError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="A bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials, settings)
    user = UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="The access token is no longer valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: RoleName) -> Callable[..., User]:
    allowed = {role.value for role in allowed_roles}

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role.name not in allowed:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="You do not have permission to perform this action.",
                details={"required_roles": sorted(allowed)},
            )
        return current_user

    return role_checker
