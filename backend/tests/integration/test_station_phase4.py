"""Station cash confirmation must use the fee the operator actually reviewed."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.modules.barriers.models import BarrierEvent
from app.modules.checkin.counter_models import CounterEvent
from app.modules.checkin.models import ParkingTransaction


def test_station_preview_timestamp_fee_change_confirmation_and_retry(
    client, db_session, operator_headers, monkeypatch
):
    lanes = client.get("/api/v1/lanes/active", headers=operator_headers).json()
    entry = next(row for row in lanes if row["direction"] == "IN")
    exit_lane = next(row for row in lanes if row["direction"] == "OUT")
    created = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": entry["id"], "license_plate": "29A12345"},
        headers={**operator_headers, "Idempotency-Key": "phase4-entry"},
    )
    assert created.status_code == 201, created.text
    transaction = db_session.get(ParkingTransaction, UUID(created.json()["transaction"]["id"]))
    check_in = datetime(2026, 11, 1, tzinfo=UTC)
    transaction.check_in_time = check_in
    transaction.price_snapshot = {
        "version_id": str(uuid4()),
        "rule_id": str(uuid4()),
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class": "VISITOR",
        "initial_fee": 5000,
        "block_fee": 2000,
    }
    db_session.commit()
    now = [check_in + timedelta(minutes=59)]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz)

    monkeypatch.setattr("app.modules.checkout.service.datetime", Clock)
    payload = {"session_id": str(transaction.id), "exit_lane_id": exit_lane["id"]}
    first = client.post("/api/v1/parking/check-out/preview", json=payload, headers=operator_headers)
    assert first.status_code == 200, first.text
    assert first.json()["fee"] == 5000
    assert first.json()["duration_minutes"] == 59
    assert datetime.fromisoformat(first.json()["exit_time"]) == now[0]
    assert datetime.fromisoformat(first.json()["check_in_time"]) == check_in

    now[0] += timedelta(minutes=2)
    headers = {**operator_headers, "Idempotency-Key": f"station-exit-{transaction.id}"}
    checkout = {**payload, "payment_method": "CASH", "expected_fee": 5000}
    changed = client.post("/api/v1/parking/check-out", json=checkout, headers=headers)
    assert changed.status_code == 409 and changed.json()["code"] == "FEE_CHANGED"
    db_session.refresh(transaction)
    assert transaction.status == "PARKED"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(BarrierEvent)
            .where(
                BarrierEvent.session_id == transaction.id,
                BarrierEvent.lane_id == UUID(exit_lane["id"]),
            )
        )
        == 0
    )

    refreshed = client.post(
        "/api/v1/parking/check-out/preview", json=payload, headers=operator_headers
    )
    assert refreshed.json()["fee"] == 7000
    checkout["expected_fee"] = 7000
    result = client.post("/api/v1/parking/check-out", json=checkout, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["fee"] == 7000
    assert result.json()["status"] == "COMPLETED" and result.json()["barrier_opened"]
    assert datetime.fromisoformat(result.json()["transaction"]["exit_time"]).tzinfo is not None
    replay = client.post("/api/v1/parking/check-out", json=checkout, headers=headers)
    assert replay.status_code == 200 and replay.json()["transaction"]["id"] == str(transaction.id)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(CounterEvent)
            .where(
                CounterEvent.session_id == transaction.id,
                CounterEvent.reason == "CHECK_OUT",
            )
        )
        == 1
    )


def test_paid_session_preview_keeps_amount_already_collected(client, db_session, operator_headers):
    lanes = client.get("/api/v1/lanes/active", headers=operator_headers).json()
    entry = next(row for row in lanes if row["direction"] == "IN")
    exit_lane = next(row for row in lanes if row["direction"] == "OUT")
    created = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": entry["id"], "license_plate": "30B99999"},
        headers={**operator_headers, "Idempotency-Key": "paid-entry"},
    )
    assert created.status_code == 201, created.text
    transaction = db_session.get(ParkingTransaction, UUID(created.json()["transaction"]["id"]))
    transaction.status = "PAID"
    transaction.fee = 5000
    transaction.check_in_time = datetime.now(UTC) - timedelta(hours=5)
    db_session.commit()
    payload = {"session_id": str(transaction.id), "exit_lane_id": exit_lane["id"]}
    preview = client.post(
        "/api/v1/parking/check-out/preview", json=payload, headers=operator_headers
    )
    assert preview.status_code == 200 and preview.json()["fee"] == 5000
    assert preview.json()["status"] == "PAID"
    assert preview.json()["fee_breakdown"] is None
    result = client.post(
        "/api/v1/parking/check-out",
        json={**payload, "expected_fee": 5000},
        headers={**operator_headers, "Idempotency-Key": f"station-exit-{transaction.id}"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["fee"] == 5000 and result.json()["barrier_opened"]
