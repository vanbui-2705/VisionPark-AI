from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.pricing.domain import (
    AccessDecision,
    PriceSnapshot,
    TicketEntitlement,
    TicketKind,
    calculate_fee,
    check_ticket_access,
)

UTC = UTC
START = datetime(2026, 10, 12, 8, tzinfo=UTC)


def rule(**changes):
    values = dict(
        version_id=uuid4(),
        rule_id=uuid4(),
        vehicle_type="CAR",
        ticket_kind="HOURLY",
        customer_class="VISITOR",
        free_minutes=15,
        initial_minutes=60,
        initial_fee=5000,
        block_minutes=30,
        block_fee=2000,
        daily_cap=15000,
        overnight_fee=3000,
        lost_ticket_fee=20000,
    )
    values.update(changes)
    return PriceSnapshot(**values)


def test_free_initial_block_and_daily_cap():
    snapshot = rule()
    assert (
        calculate_fee(
            check_in=START, check_out=START + timedelta(minutes=15), snapshot=snapshot
        ).total
        == 0
    )
    assert (
        calculate_fee(
            check_in=START, check_out=START + timedelta(minutes=16), snapshot=snapshot
        ).total
        == 5000
    )
    assert (
        calculate_fee(
            check_in=START, check_out=START + timedelta(minutes=76), snapshot=snapshot
        ).total
        == 7000
    )
    assert (
        calculate_fee(
            check_in=START, check_out=START + timedelta(hours=10), snapshot=snapshot
        ).total
        == 15000
    )


def test_overnight_and_lost_ticket_are_separate_lines():
    snapshot = rule()
    result = calculate_fee(
        check_in=START,
        check_out=START + timedelta(days=1),
        snapshot=snapshot,
        lost_ticket=True,
    )
    assert [line.code for line in result.lines] == ["PARKING_DAY", "OVERNIGHT", "LOST_TICKET"]
    assert result.total == 38000
    assert result.price_version_id == snapshot.version_id


def test_invalid_price_and_time_rejected():
    with pytest.raises(ValidationError):
        rule(daily_cap=4000)
    with pytest.raises(ValidationError):
        rule(
            windows=[
                {"start_minute": 0, "end_minute": 120},
                {"start_minute": 60, "end_minute": 180},
            ]
        )
    with pytest.raises(ValueError):
        calculate_fee(check_in=START, check_out=START - timedelta(minutes=1), snapshot=rule())


def test_monthly_ticket_valid_grace_expired_plate_and_zone():
    zone = uuid4()
    ticket = TicketEntitlement(
        kind=TicketKind.MONTHLY,
        plate="29A12345",
        zone_id=zone,
        valid_from=START,
        valid_until=START + timedelta(days=30),
    )

    def check(**kw):
        return check_ticket_access(
            ticket,
            at=kw.get("at", START + timedelta(days=20)),
            plate=kw.get("plate", "29A12345"),
            ticket_code=None,
            zone_id=kw.get("zone_id", zone),
        )

    assert check().decision == AccessDecision.ALLOW
    assert check(at=START + timedelta(days=32)).reason == "GRACE_PERIOD"
    assert check(at=START + timedelta(days=34)).reason == "EXPIRED"
    assert check(plate="OTHER").reason == "PLATE_MISMATCH"
    assert check(zone_id=uuid4()).reason == "WRONG_ZONE"


def test_registered_pass_only_charges_after_expiry():
    snapshot = rule(
        ticket_kind=TicketKind.MONTHLY,
        month_pass_fee=100000,
        entitlement_valid_until=START + timedelta(hours=2),
    )
    covered = calculate_fee(check_in=START, check_out=START + timedelta(hours=1), snapshot=snapshot)
    assert covered.total == 0
    overage = calculate_fee(check_in=START, check_out=START + timedelta(hours=3), snapshot=snapshot)
    assert overage.total == 5000
    assert overage.lines[0].code == "PASS_OVERAGE"
