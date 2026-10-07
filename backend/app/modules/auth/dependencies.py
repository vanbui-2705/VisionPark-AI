from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_claims
from app.database.session import get_db
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import RoleName

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
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

    claims = decode_access_claims(credentials.credentials, settings)
    from uuid import UUID

    user_id = UUID(claims["sub"])
    user = UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active or claims.get("ver", 0) != user.token_version:
        raise AppError(
            status_code=401,
            code="UNAUTHENTICATED",
            message="The access token is no longer valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.actor_id = user.id
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
