from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .domain import PriceWindow, TicketKind


class CustomerClassCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    discount_percent: int = Field(default=0, ge=0, le=100)


class TicketProductCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    kind: TicketKind
    vehicle_type: str = Field(min_length=1, max_length=40)
    customer_class_id: UUID | None = None
    requires_vehicle: bool = False
    sale_limit: int | None = Field(default=None, ge=0)
    active: bool = True


class PricingRuleInput(BaseModel):
    vehicle_type: str = Field(min_length=1, max_length=40)
    ticket_kind: TicketKind
    customer_class_id: UUID
    free_minutes: int = Field(default=0, ge=0)
    initial_minutes: int = Field(default=60, gt=0)
    initial_fee: int = Field(ge=0)
    block_minutes: int = Field(default=60, gt=0)
    block_fee: int = Field(ge=0)
    daily_cap: int | None = Field(default=None, ge=0)
    overnight_fee: int = Field(default=0, ge=0)
    lost_ticket_fee: int = Field(default=0, ge=0)
    overtime_fee: int = Field(default=0, ge=0)
    day_pass_fee: int = Field(default=0, ge=0)
    month_pass_fee: int = Field(default=0, ge=0)
    windows: list[PriceWindow] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_cap_and_windows(self) -> "PricingRuleInput":
        if self.daily_cap is not None and self.daily_cap < self.initial_fee:
            raise ValueError("Daily cap must not be below the initial fee")
        ordered = sorted(self.windows, key=lambda window: window.start_minute)
        if any(
            left.end_minute > right.start_minute
            for left, right in zip(ordered, ordered[1:], strict=False)
        ):
            raise ValueError("Price windows must not overlap")
        return self


class PricingVersionCreate(BaseModel):
    active_from: datetime
    rules: list[PricingRuleInput] = Field(min_length=1)

    @model_validator(mode="after")
    def require_timezone(self) -> "PricingVersionCreate":
        if self.active_from.tzinfo is None:
            raise ValueError("active_from must include a timezone")
        keys = [(r.vehicle_type, r.ticket_kind, r.customer_class_id) for r in self.rules]
        if len(keys) != len(set(keys)):
            raise ValueError("Rules in one version must be unique")
        return self


class PricingPreviewRequest(BaseModel):
    vehicle_type: str
    ticket_kind: TicketKind
    customer_class_id: UUID
    check_in: datetime
    check_out: datetime
    lost_ticket: bool = False
    overtime: bool = False
    extra_free_minutes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_times(self) -> "PricingPreviewRequest":
        if self.check_in.tzinfo is None or self.check_out.tzinfo is None:
            raise ValueError("Check-in and check-out must include timezones")
        if self.check_out <= self.check_in:
            raise ValueError("Check-out must follow check-in")
        return self
