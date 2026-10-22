from datetime import time
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.buildings.schemas import BuildingCreate


class VehicleType(StrEnum):
    CAR = "CAR"
    MOTORBIKE = "MOTORBIKE"
    BICYCLE = "BICYCLE"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OperatingWindow(StrictModel):
    weekday: int = Field(ge=0, le=6)
    start: time
    end: time

    @model_validator(mode="after")
    def forward_window(self):
        if self.start >= self.end:
            raise ValueError("Split overnight operating hours at midnight.")
        return self


class LotInformation(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=512)
    timezone: str = "Asia/Ho_Chi_Minh"
    status: Literal["OPEN", "CLOSED", "MAINTENANCE"] = "OPEN"
    operating_hours: list[OperatingWindow] = Field(default_factory=list)

    _timezone = field_validator("timezone")(BuildingCreate.valid_timezone.__func__)

    @field_validator("operating_hours")
    @classmethod
    def no_overlap(cls, windows):
        for day in range(7):
            ordered = sorted((w for w in windows if w.weekday == day), key=lambda w: w.start)
            if any(a.end > b.start for a, b in zip(ordered, ordered[1:], strict=False)):
                raise ValueError("Operating hours must not overlap.")
        return windows


class Capacity(StrictModel):
    physical_capacity: int = Field(default=0, ge=0, le=1000000)
    safe_capacity: int = Field(default=0, ge=0, le=1000000)
    nearly_full_threshold: float = Field(default=80, gt=0, le=100)
    full_threshold: float = Field(default=95, gt=0, le=100)

    @model_validator(mode="after")
    def valid_capacity(self):
        if self.safe_capacity > self.physical_capacity:
            raise ValueError("Safe capacity cannot exceed physical capacity.")
        if self.nearly_full_threshold > self.full_threshold:
            raise ValueError("Nearly full threshold cannot exceed full threshold.")
        return self


class ClassQuota(StrictModel):
    residents: int = Field(default=0, ge=0)
    employees: int = Field(default=0, ge=0)
    visitors: int = Field(default=0, ge=0)


class AIThresholds(StrictModel):
    vehicle_confidence: float | None = Field(default=None, ge=0, le=1)
    plate_confidence: float | None = Field(default=None, ge=0, le=1)


class FireSettings(StrictModel):
    fire_confidence: float | None = Field(default=None, ge=0, le=1)
    smoke_confidence: float | None = Field(default=None, ge=0, le=1)
    confirmation_frames: int | None = Field(default=None, ge=1, le=10000)
    confirmation_window_seconds: float | None = Field(default=None, gt=0, le=3600)
    alert_recipients: list[UUID] = Field(default_factory=list, max_length=100)
    areas: list[str] = Field(default_factory=list, max_length=100)
    escape_exits: list[str] = Field(default_factory=list, max_length=100)


class LotSettings(StrictModel):
    schema_version: Literal[1] = 1
    information: LotInformation
    capacities: dict[VehicleType, Capacity] = Field(
        default_factory=lambda: {v: Capacity() for v in VehicleType}
    )
    quotas: dict[VehicleType, ClassQuota] = Field(
        default_factory=lambda: {v: ClassQuota() for v in VehicleType}
    )
    ai: AIThresholds = Field(default_factory=AIThresholds)
    fire: FireSettings = Field(default_factory=FireSettings)

    @model_validator(mode="after")
    def valid_quotas(self):
        if set(self.capacities) != set(VehicleType) or set(self.quotas) != set(VehicleType):
            raise ValueError("Configure all three vehicle types.")
        for kind, quota in self.quotas.items():
            if sum(quota.model_dump().values()) > self.capacities[kind].safe_capacity:
                raise ValueError(f"Total quota exceeds safe capacity for {kind}.")
        return self


class SettingsUpdate(StrictModel):
    revision: int = Field(ge=0)
    settings: LotSettings


class SettingsCopy(StrictModel):
    target_building_id: UUID
    source_revision: int = Field(ge=0)
    target_revision: int = Field(ge=0)


class Readiness(StrictModel):
    ready: bool
    missing: list[str]


class SettingsPublic(StrictModel):
    building_id: UUID
    revision: int
    settings: LotSettings
    readiness: Readiness


def default_settings(building) -> LotSettings:
    return LotSettings(
        information=LotInformation(
            name=building.name, address=building.address, timezone=building.timezone
        )
    )
