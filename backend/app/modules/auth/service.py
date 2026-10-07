from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.users.repository import UserRepository
from app.modules.users.service import to_public_user

# A fixed Argon2id hash keeps the missing-user path close to the bad-password path.
_DUMMY_PASSWORD_HASH = hash_password("visionpark-dummy-password")


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    def login(self, credentials: LoginRequest) -> TokenResponse:
        user = self.users.get_by_username(credentials.username)
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = verify_password(credentials.password, password_hash)

        if user is None or not password_matches or not user.is_active:
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Username or password is incorrect.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(user)

        token = create_access_token(user.id, self.settings, token_version=user.token_version)
        return TokenResponse(
            access_token=token,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=to_public_user(user),
        )
