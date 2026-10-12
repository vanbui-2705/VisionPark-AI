"""Pure pricing and ticket decisions used by preview and check-out."""

from datetime import datetime, timedelta
from enum import StrEnum
from math import ceil
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TicketKind(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    NIGHT = "NIGHT"


class AccessDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


class PriceWindow(BaseModel):
    start_minute: int = Field(ge=0, lt=1440)
    end_minute: int = Field(gt=0, le=1440)

    @model_validator(mode="after")
    def check_order(self) -> "PriceWindow":
        if self.end_minute <= self.start_minute:
            raise ValueError("Price window must end after it starts")
        return self


class PriceSnapshot(BaseModel):
    version_id: UUID
    rule_id: UUID
    vehicle_type: str = Field(min_length=1)
    ticket_kind: TicketKind
    customer_class: str = Field(min_length=1)
    discount_percent: int = Field(default=0, ge=0, le=100)
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
    entitlement_valid_until: datetime | None = None

    @model_validator(mode="after")
    def check_rule(self) -> "PriceSnapshot":
        if self.daily_cap is not None and self.daily_cap < self.initial_fee:
            raise ValueError("Daily cap must not be below the initial fee")
        ordered = sorted(self.windows, key=lambda item: item.start_minute)
        if any(
            left.end_minute > right.start_minute
            for left, right in zip(ordered, ordered[1:], strict=False)
        ):
            raise ValueError("Price windows must not overlap")
        return self


class FeeLine(BaseModel):
    code: str
    amount: int
    quantity: int = Field(ge=0)

    @model_validator(mode="after")
    def check_amount(self) -> "FeeLine":
        if self.amount < 0 and self.code != "DISCOUNT":
            raise ValueError("Only discount lines may be negative")
        return self


class FeeResult(BaseModel):
    total: int = Field(ge=0)
    currency: str = "VND"
    price_version_id: UUID
    lines: list[FeeLine]


class TicketEntitlement(BaseModel):
    kind: TicketKind
    plate: str | None = None
    ticket_code: str | None = None
    zone_id: UUID | None = None
    valid_from: datetime
    valid_until: datetime
    grace_days: int = Field(default=3, ge=0)
    invite_free_minutes: int = Field(default=0, ge=0)


class AccessResult(BaseModel):
    decision: AccessDecision
    reason: str
    free_minutes: int = 0


def check_ticket_access(
    ticket: TicketEntitlement | None,
    *,
    at: datetime,
    plate: str | None,
    ticket_code: str | None,
    zone_id: UUID | None,
) -> AccessResult:
    if ticket is None:
        return AccessResult(decision=AccessDecision.REVIEW, reason="NO_TICKET")
    if at.tzinfo is None or ticket.valid_from.tzinfo is None or ticket.valid_until.tzinfo is None:
        raise ValueError("Ticket and access times must include a timezone")
    if ticket.valid_until < ticket.valid_from:
        raise ValueError("Ticket validity range is reversed")
    if ticket.zone_id is not None and ticket.zone_id != zone_id:
        return AccessResult(decision=AccessDecision.DENY, reason="WRONG_ZONE")
    if ticket.plate and (plate or "").upper() != ticket.plate.upper():
        return AccessResult(decision=AccessDecision.REVIEW, reason="PLATE_MISMATCH")
    if ticket.ticket_code and ticket.ticket_code != ticket_code:
        return AccessResult(decision=AccessDecision.REVIEW, reason="TICKET_CODE_MISMATCH")
    if at < ticket.valid_from:
        return AccessResult(decision=AccessDecision.DENY, reason="NOT_YET_VALID")
    if at <= ticket.valid_until:
        return AccessResult(
            decision=AccessDecision.ALLOW,
            reason="VALID",
            free_minutes=ticket.invite_free_minutes,
        )
    if ticket.kind == TicketKind.MONTHLY and at <= ticket.valid_until + timedelta(
        days=ticket.grace_days
    ):
        return AccessResult(decision=AccessDecision.ALLOW, reason="GRACE_PERIOD")
    return AccessResult(decision=AccessDecision.DENY, reason="EXPIRED")


def calculate_fee(
    *,
    check_in: datetime,
    check_out: datetime,
    snapshot: PriceSnapshot,
    lost_ticket: bool = False,
    overtime: bool = False,
    extra_free_minutes: int = 0,
) -> FeeResult:
    if check_in.tzinfo is None or check_out.tzinfo is None:
        raise ValueError("Check-in and check-out times must include a timezone")
    if check_out < check_in:
        raise ValueError("Check-out cannot precede check-in")
    if extra_free_minutes < 0:
        raise ValueError("Extra free minutes cannot be negative")

    minutes = ceil((check_out - check_in).total_seconds() / 60)
    billable = max(0, minutes - snapshot.free_minutes - extra_free_minutes)
    lines: list[FeeLine] = []
    if snapshot.entitlement_valid_until is not None and snapshot.ticket_kind in {
        TicketKind.DAILY,
        TicketKind.MONTHLY,
    }:
        until = snapshot.entitlement_valid_until
        if until.tzinfo is None:
            raise ValueError("Pass validity must include a timezone")
        overage_start = max(check_in, until)
        overage_minutes = max(
            0,
            ceil((check_out - overage_start).total_seconds() / 60)
            - snapshot.free_minutes
            - extra_free_minutes,
        )
        remaining = overage_minutes
        day_index = 0
        while remaining:
            chunk = min(remaining, 1440)
            blocks = ceil(max(0, chunk - snapshot.initial_minutes) / snapshot.block_minutes)
            amount = snapshot.initial_fee + blocks * snapshot.block_fee
            if snapshot.daily_cap is not None:
                amount = min(amount, snapshot.daily_cap)
            lines.append(FeeLine(code="PASS_OVERAGE", amount=amount, quantity=day_index + 1))
            remaining -= chunk
            day_index += 1
    elif snapshot.ticket_kind == TicketKind.DAILY:
        days = max(1, ceil(billable / 1440)) if billable else 0
        lines.append(FeeLine(code="DAY_PASS", amount=days * snapshot.day_pass_fee, quantity=days))
    elif snapshot.ticket_kind == TicketKind.MONTHLY:
        months = max(1, ceil(billable / (30 * 1440))) if billable else 0
        lines.append(
            FeeLine(code="MONTH_PASS", amount=months * snapshot.month_pass_fee, quantity=months)
        )
    else:
        remaining = billable
        day_index = 0
        while remaining:
            chunk = min(remaining, 1440)
            initial = snapshot.initial_fee if chunk else 0
            blocks = ceil(max(0, chunk - snapshot.initial_minutes) / snapshot.block_minutes)
            amount = initial + blocks * snapshot.block_fee
            if snapshot.daily_cap is not None:
                amount = min(amount, snapshot.daily_cap)
            lines.append(FeeLine(code="PARKING_DAY", amount=amount, quantity=day_index + 1))
            remaining -= chunk
            day_index += 1

    overnight_start = check_in
    if snapshot.entitlement_valid_until is not None:
        overnight_start = max(check_in, snapshot.entitlement_valid_until)
    nights = (
        check_out.astimezone(check_in.tzinfo).date()
        - overnight_start.astimezone(check_in.tzinfo).date()
    ).days
    if nights > 0 and snapshot.overnight_fee:
        lines.append(
            FeeLine(code="OVERNIGHT", amount=nights * snapshot.overnight_fee, quantity=nights)
        )
    if lost_ticket and snapshot.lost_ticket_fee:
        lines.append(FeeLine(code="LOST_TICKET", amount=snapshot.lost_ticket_fee, quantity=1))
    if overtime and snapshot.overtime_fee:
        lines.append(FeeLine(code="OVERTIME", amount=snapshot.overtime_fee, quantity=1))
    eligible = sum(
        line.amount
        for line in lines
        if line.code in {"PARKING_DAY", "DAY_PASS", "MONTH_PASS", "PASS_OVERAGE"}
    )
    discount = eligible * snapshot.discount_percent // 100
    if discount:
        lines.append(FeeLine(code="DISCOUNT", amount=-discount, quantity=1))
    return FeeResult(
        total=sum(line.amount for line in lines),
        price_version_id=snapshot.version_id,
        lines=lines,
    )
