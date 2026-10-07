from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleName(StrEnum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    ACCOUNTANT = "ACCOUNTANT"
    TECHNICIAN = "TECHNICIAN"


class UserPublic(BaseModel):
    id: UUID
    username: str
    display_name: str
    role: RoleName
    is_active: bool
    email: str | None = None
    last_login_at: datetime | None


class ManagedUserPublic(UserPublic):
    email: str | None
    created_at: datetime


class UserFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("username", check_fields=False)
    @classmethod
    def normalize_username(cls, value: str) -> str:
        import re

        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", value):
            raise ValueError(
                "Username must contain 3 to 64 letters, digits, dots, underscores or hyphens."
            )
        return value

    @field_validator("display_name", check_fields=False)
    @classmethod
    def normalize_name(cls, value: str) -> str:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Display name must not be blank.")
        return value

    @field_validator("email", check_fields=False)
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email address.")
        return value


class UserCreate(UserFields):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(None, max_length=254)
    role: RoleName = RoleName.OPERATOR
    active: bool = True


class UserUpdate(UserFields):
    display_name: str | None = Field(None, min_length=1, max_length=120)
    email: str | None = Field(None, max_length=254)
    password: str | None = Field(None, min_length=8, max_length=128)
    role: RoleName | None = None
    active: bool | None = None

    @field_validator("display_name", "password", "role", "active")
    @classmethod
    def non_nullable_fields(cls, value):
        if value is None:
            raise ValueError("This field cannot be null.")
        return value


class RegistrationRequest(UserFields):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(None, max_length=254)
    password: str = Field(min_length=8, max_length=128)
