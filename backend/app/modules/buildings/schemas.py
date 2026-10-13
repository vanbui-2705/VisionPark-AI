from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BuildingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=512)
    timezone: str = "Asia/Ho_Chi_Minh"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use an IANA timezone.") from exc
        return value


class BuildingPublic(BuildingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool


class BuildingState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class BuildingAdminCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    role: Literal["BUILDING_ADMIN"] = "BUILDING_ADMIN"
