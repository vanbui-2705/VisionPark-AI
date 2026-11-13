from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.database.session import get_db
from app.database.tenant import resolve_building
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.auth.service import AuthService
from app.modules.users.schemas import RegistrationRequest, UserPublic
from app.modules.users.service import to_public_user

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=201)
def register(
    payload: RegistrationRequest,
):
    raise AppError(
        status_code=403,
        code="REGISTRATION_DISABLED",
        message="Public registration is disabled. Contact an administrator.",
    )


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    return AuthService(session, settings).login(credentials)


@router.get("/me", response_model=UserPublic)
def read_current_user(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> UserPublic:
    public_user = to_public_user(current_user)

    building_id = session.info.get("building_id")

    if not isinstance(building_id, UUID):
        building_id = resolve_building(session, current_user)

    return public_user.model_copy(
        update={"building_id": building_id}
    )