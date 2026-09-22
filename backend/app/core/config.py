from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "development-only-change-this-jwt-secret"


class Settings(BaseSettings):
    """Environment-backed application settings.

    Local defaults make the process bootable before Docker Compose exists. Production rejects the
    development JWT secret, and demo accounts are created only when ``auto_seed`` is explicitly on.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "VisionPark API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://visionpark:visionpark@localhost:5432/visionpark"
    database_echo: bool = False

    jwt_secret_key: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"
    upload_max_bytes: int = 5 * 1024 * 1024
    local_storage_path: str = "./var/media"
    alpr_provider: str = "mock"

    auto_seed: bool = False
    seed_admin_username: str = "admin"
    seed_admin_password: SecretStr | None = None
    seed_operator_username: str = "operator"
    seed_operator_password: SecretStr | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
        if len(self.jwt_secret_key.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        if self.environment == "production" and (
            self.jwt_secret_key.get_secret_value() == DEV_JWT_SECRET
        ):
            raise ValueError("Production must provide a non-development JWT_SECRET_KEY")
        if self.auto_seed and (
            self.seed_admin_password is None or self.seed_operator_password is None
        ):
            raise ValueError("Demo account passwords are required when AUTO_SEED=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
