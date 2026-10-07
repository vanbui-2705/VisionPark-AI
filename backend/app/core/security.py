from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import AppError

password_hasher = PasswordHasher(
    type=Type.ID,
    memory_cost=16384,  # Giảm memory cost xuống 16MB để tránh lỗi trên Windows
    time_cost=2,
    parallelism=1,
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(
    subject: UUID,
    settings: Settings,
    *,
    expires_delta: timedelta | None = None,
    token_version: int = 0,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    claims = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid4()),
        "ver": token_version,
    }
    return jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_claims(token: str, settings: Settings) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if claims.get("type") != "access":
            raise jwt.InvalidTokenError("Unexpected token type")
        UUID(str(claims["sub"]))
        return claims
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Access token is invalid or expired.",
            status_code=401,
        ) from exc


def decode_access_token(token: str, settings: Settings) -> UUID:
    return UUID(decode_access_claims(token, settings)["sub"])
