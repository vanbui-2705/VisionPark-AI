from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEV_JWT_SECRET = "development-only-change-this-jwt-secret"


class Settings(BaseSettings):
    """Environment-backed application settings.

    Database credentials and the JWT signing key must be supplied explicitly in every environment.
    Initial administrator is created only when ``auto_seed`` is explicitly on.
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

    database_url: str = Field(min_length=1)
    database_echo: bool = False

    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"
    upload_max_bytes: int = 5 * 1024 * 1024
    local_storage_path: str = "./var/media"
    alpr_provider: Literal["real"] = "real"
    alpr_manifest_path: str = "models/alpr-manifest.json"
    alpr_device: str = "cpu"
    alpr_detector_confidence: float = 0.25
    alpr_confidence_threshold: float = 0.85
    alpr_ocr_margin: float = 0.08
    alpr_ocr_enabled: bool = True

    auto_seed: bool = False
    public_registration_enabled: bool = False
    seed_admin_username: str = "admin"
    seed_admin_password: SecretStr | None = None
    seed_operator_username: str = "operator"
    seed_operator_password: SecretStr | None = None

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, value: object) -> object:
        """Accept common deployment mode values from inherited shell environments."""
        if isinstance(value, str) and value.strip().casefold() in {"release", "production", "off"}:
            return False
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()
        try:
            make_url(value)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy connection URL") from exc
        return value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
        if not 0 < self.alpr_detector_confidence <= 1:
            raise ValueError("ALPR_DETECTOR_CONFIDENCE must be between 0 and 1")
        if not 0 < self.alpr_confidence_threshold <= 1:
            raise ValueError("ALPR_CONFIDENCE_THRESHOLD must be between 0 and 1")
        if not 0 <= self.alpr_ocr_margin <= 1:
            raise ValueError("ALPR_OCR_MARGIN must be between 0 and 1")
        if len(self.jwt_secret_key.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        if self.jwt_secret_key.get_secret_value() in {
            DEV_JWT_SECRET,
            "replace-this-with-a-long-random-secret",
        }:
            raise ValueError("JWT_SECRET_KEY must not use a sample or development signing key")
        if self.auto_seed and (
            self.seed_admin_password is None or len(self.seed_admin_password.get_secret_value()) < 8
        ):
            raise ValueError(
                "An administrator password of at least 8 characters is required when AUTO_SEED=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
