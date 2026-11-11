"""Integration tests for Backend Core (Member 2 - dqt_core) Demo Readiness Plan items:
- BUILD-01: Dedicated IdempotencyRecord table, replay, conflict detection, and key resolution
- BUILD-02 / IMPROVE-01 / IMPROVE-02: Unified Checkout/Invoice/Payment ledger and atomic rollback
- BUILD-04 / DEMO-10: Idempotent DEMO-BUILDING acceptance environment seed & E2E workflows
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.database.idempotency import IdempotencyOperation, IdempotencyRecord
from app.modules.buildings.models import DEFAULT_BUILDING_ID, Building
from app.modules.checkin.counter_models import ParkingCounter
from app.modules.checkin.counter_service import CounterService
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.lanes.models import Lane
from app.modules.pricing.models import CustomerClass, Invoice, Payment, Subscription, Vehicle
from scripts.seed_demo_environment import (
    DEMO_ADMIN_USERNAME,
    DEMO_BUILDING_CODE,
    DEMO_MONTHLY_PLATE,
    DEMO_OPERATOR_USERNAME,
    apply_demo_environment,
    check_demo_environment,
    verify_safe_target_database,
)


def _login(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _get_lanes(client, headers: dict[str, str]) -> tuple[str, str]:
    response = client.get("/api/v1/lanes/active", headers=headers)
    assert response.status_code == 200, response.text
    lanes = response.json()
    in_lane = next(row for row in lanes if row["direction"] == "IN")
    out_lane = next(row for row in lanes if row["direction"] == "OUT")
    return in_lane["id"], out_lane["id"]


def _backdate_checkin(db_session, tx_id: UUID, minutes: int = 65) -> None:
    tx = db_session.get(ParkingTransaction, tx_id)
    assert tx is not None
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=minutes)
    db_session.commit()


def test_build_01_idempotency_record_persisted_replayed_and_conflict_blocked(client, db_session):
    headers = _login(client, "operator", "operator-test-password")
    in_lane_id, out_lane_id = _get_lanes(client, headers)

    res_in = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": in_lane_id, "license_plate": "30A-601.01", "vehicle_type": "CAR"},
        headers={**headers, "Idempotency-Key": f"in-{uuid4()}"},
    )
    assert res_in.status_code == 201, res_in.text
    tx_id = UUID(res_in.json()["transaction"]["id"])
    _backdate_checkin(db_session, tx_id, minutes=65)

    # Mismatched header vs body Idempotency-Key -> 422 IDEMPOTENCY_KEY_MISMATCH
    mismatch_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "session_id": str(tx_id),
            "exit_lane_id": out_lane_id,
            "payment_method": "CASH",
            "idempotency_key": "body-key-001",
        },
        headers={**headers, "Idempotency-Key": "header-key-002"},
    )
    assert mismatch_res.status_code == 422
    assert mismatch_res.json()["code"] == "IDEMPOTENCY_KEY_MISMATCH"

    checkout_key = f"co-record-{tx_id}"
    payload = {
        "session_id": str(tx_id),
        "exit_lane_id": out_lane_id,
        "payment_method": "CASH",
    }
    res1 = client.post(
        "/api/v1/parking/check-out",
        json=payload,
        headers={**headers, "Idempotency-Key": checkout_key},
    )
    assert res1.status_code == 200, res1.text
    body1 = res1.json()
    assert body1["status"] == "COMPLETED"
    assert body1["invoice_id"] is not None
    assert body1["payment_id"] is not None

    db_session.expire_all()
    idem_row = db_session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.operation == IdempotencyOperation.CHECKOUT,
            IdempotencyRecord.key == checkout_key,
        )
    )
    assert idem_row is not None
    assert idem_row.transaction_id == tx_id
    assert idem_row.status == TransactionStatus.COMPLETED

    # Replay with identical key and payload -> 200 OK with identical invoice/payment IDs
    res2 = client.post(
        "/api/v1/parking/check-out",
        json=payload,
        headers={**headers, "Idempotency-Key": checkout_key},
    )
    assert res2.status_code == 200, res2.text
    body2 = res2.json()
    assert body2["invoice_id"] == body1["invoice_id"]
    assert body2["payment_id"] == body1["payment_id"]

    # Conflict with same key and different payload -> 409 IDEMPOTENCY_KEY_REUSED
    res3 = client.post(
        "/api/v1/parking/check-out",
        json={**payload, "is_lost_ticket": True},
        headers={**headers, "Idempotency-Key": checkout_key},
    )
    assert res3.status_code == 409
    assert res3.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_build_01_and_build_02_payment_pending_invoice_and_record_payment_idempotency(
    client, db_session
):
    headers = _login(client, "operator", "operator-test-password")
    in_lane_id, out_lane_id = _get_lanes(client, headers)

    res_in = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": in_lane_id, "license_plate": "30A-602.02", "vehicle_type": "CAR"},
        headers={**headers, "Idempotency-Key": f"in-{uuid4()}"},
    )
    assert res_in.status_code == 201
    tx_id = UUID(res_in.json()["transaction"]["id"])
    _backdate_checkin(db_session, tx_id, minutes=65)

    # Step 1: Checkout without payment_method -> PAYMENT_PENDING + Invoice(status=PENDING)
    pending_key = f"co-pending-{tx_id}"
    pending_payload = {"session_id": str(tx_id), "exit_lane_id": out_lane_id}
    res_pending = client.post(
        "/api/v1/parking/check-out",
        json=pending_payload,
        headers={**headers, "Idempotency-Key": pending_key},
    )
    assert res_pending.status_code == 200, res_pending.text
    pending_body = res_pending.json()
    assert pending_body["status"] == "PAYMENT_PENDING"
    assert pending_body["invoice_id"] is not None
    due_fee = float(pending_body["fee"])
    assert due_fee > 0

    # Replay PAYMENT_PENDING with same key -> returns PAYMENT_PENDING idempotently
    res_pending_replay = client.post(
        "/api/v1/parking/check-out",
        json=pending_payload,
        headers={**headers, "Idempotency-Key": pending_key},
    )
    assert res_pending_replay.status_code == 200
    assert res_pending_replay.json()["status"] == "PAYMENT_PENDING"
    assert res_pending_replay.json()["invoice_id"] == pending_body["invoice_id"]

    db_session.expire_all()
    inv_pending = db_session.scalar(select(Invoice).where(Invoice.transaction_id == tx_id))
    assert inv_pending is not None
    assert inv_pending.status == "PENDING"

    # Step 2: Record payment with Idempotency-Key -> COMPLETED + Invoice(PAID) + Payment(PAID)
    pay_key = f"pay-{tx_id}"
    pay_payload = {
        "payment_method": "VIETQR_MOCK",
        "amount": due_fee,
        "provider_ref": "VQR-DEMO-001",
    }
    res_pay = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json=pay_payload,
        headers={**headers, "Idempotency-Key": pay_key},
    )
    assert res_pay.status_code == 200, res_pay.text
    pay_body = res_pay.json()
    assert pay_body["status"] == "COMPLETED"
    assert pay_body["invoice_id"] == pending_body["invoice_id"]
    assert pay_body["payment_id"] is not None

    # Replay record_payment with same key -> 200 OK without duplicate Payment
    res_pay_replay = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json=pay_payload,
        headers={**headers, "Idempotency-Key": pay_key},
    )
    assert res_pay_replay.status_code == 200, res_pay_replay.text
    assert res_pay_replay.json()["payment_id"] == pay_body["payment_id"]

    # Reuse same payment Idempotency-Key with mutated amount -> 409 IDEMPOTENCY_KEY_REUSED
    res_pay_conflict = client.post(
        f"/api/v1/parking/sessions/{tx_id}/payments",
        json={**pay_payload, "amount": due_fee + 5000},
        headers={**headers, "Idempotency-Key": pay_key},
    )
    assert res_pay_conflict.status_code == 409
    assert res_pay_conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

    db_session.expire_all()
    inv_paid = db_session.scalar(select(Invoice).where(Invoice.transaction_id == tx_id))
    assert inv_paid is not None and inv_paid.status == "PAID"
    pay_count = db_session.scalar(
        select(func.count()).select_from(Payment).where(Payment.invoice_id == inv_paid.id)
    )
    assert pay_count == 1


def test_improve_02_atomic_rollback_on_checkout_failure(client, db_session, monkeypatch):
    headers = _login(client, "operator", "operator-test-password")
    in_lane_id, out_lane_id = _get_lanes(client, headers)

    res_in = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": in_lane_id, "license_plate": "30A-603.03", "vehicle_type": "CAR"},
        headers={**headers, "Idempotency-Key": f"in-{uuid4()}"},
    )
    assert res_in.status_code == 201
    tx_id = UUID(res_in.json()["transaction"]["id"])
    _backdate_checkin(db_session, tx_id, minutes=65)

    def _boom(*args, **kwargs):
        raise RuntimeError("Simulated counter failure during checkout")

    monkeypatch.setattr(CounterService, "decrement_atomic", _boom)

    fail_key = f"co-rollback-{tx_id}"
    with pytest.raises(RuntimeError, match="Simulated counter failure"):
        client.post(
            "/api/v1/parking/check-out",
            json={
                "session_id": str(tx_id),
                "exit_lane_id": out_lane_id,
                "payment_method": "CASH",
            },
            headers={**headers, "Idempotency-Key": fail_key},
        )

    db_session.expire_all()
    tx = db_session.get(ParkingTransaction, tx_id)
    assert tx is not None
    assert tx.status == TransactionStatus.PARKED
    assert db_session.scalar(select(Invoice).where(Invoice.transaction_id == tx_id)) is None
    assert (
        db_session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == fail_key))
        is None
    )


def test_build_02_free_checkout_syncs_invoice_ledger(client, db_session):
    admin_headers = _login(client, "admin", "admin-test-password")
    in_lane_id, out_lane_id = _get_lanes(client, admin_headers)

    # Free check-in and immediate checkout within free_minutes (0 VND)
    res_in = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": in_lane_id, "license_plate": "30A-604.04", "vehicle_type": "CAR"},
        headers={**admin_headers, "Idempotency-Key": f"in-{uuid4()}"},
    )
    assert res_in.status_code == 201
    tx_id = UUID(res_in.json()["transaction"]["id"])

    res_out = client.post(
        "/api/v1/parking/check-out",
        json={"session_id": str(tx_id), "exit_lane_id": out_lane_id},
        headers={**admin_headers, "Idempotency-Key": f"out-{tx_id}"},
    )
    assert res_out.status_code == 200, res_out.text
    assert res_out.json()["fee"] == 0.0
    assert res_out.json()["status"] == "COMPLETED"
    assert res_out.json()["invoice_id"] is not None

    building = db_session.get(Building, DEFAULT_BUILDING_ID)
    if building is not None:
        building.timezone = "UTC"
        db_session.commit()

    today_str = datetime.now(UTC).date().isoformat()
    rebuild_res = client.post(
        f"/api/v1/m5/daily-stats/rebuild?building_id={DEFAULT_BUILDING_ID}&day={today_str}",
        headers=admin_headers,
    )
    assert rebuild_res.status_code == 200, rebuild_res.text
    stat = rebuild_res.json()
    assert int(stat["entries"]) >= 1
    assert int(stat["exits"]) >= 1


def test_build_04_demo_10_seed_demo_environment_idempotent_and_e2e_workflow(client, db_session):
    # Production safety guard check
    with pytest.raises(RuntimeError, match="Refusing to run demo seed"):
        verify_safe_target_database(
            "postgresql+psycopg://user:pass@prod-db.example.com:5432/visionpark",
            environment="production",
        )

    # 1. --check before seed -> ready=False
    pre_check = check_demo_environment(db_session, building_code=DEMO_BUILDING_CODE)
    assert pre_check["ready"] is False
    assert len(pre_check["issues"]) > 0

    # 2. --apply twice consecutively -> idempotent, ready=True, no duplicate records
    apply_1 = apply_demo_environment(
        db_session,
        building_code=DEMO_BUILDING_CODE,
        admin_password="demo-admin-password-123",
        operator_password="demo-operator-password-123",
    )
    assert apply_1["ready"] is True, apply_1["issues"]

    apply_2 = apply_demo_environment(
        db_session,
        building_code=DEMO_BUILDING_CODE,
        admin_password="demo-admin-password-123",
        operator_password="demo-operator-password-123",
    )
    assert apply_2["ready"] is True, apply_2["issues"]

    demo_building_id = UUID(apply_2["details"]["building_id"])
    lane_in_id = apply_2["details"]["lane_in_id"]
    lane_out_id = apply_2["details"]["lane_out_id"]
    std_class_id = apply_2["details"]["customer_class_id"]

    # Verify no duplicate lanes, classes, vehicles, or subscriptions
    assert (
        db_session.scalar(
            select(func.count()).select_from(Lane).where(Lane.building_id == demo_building_id)
        )
        == 2
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(CustomerClass)
            .where(CustomerClass.building_id == demo_building_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Vehicle).where(Vehicle.building_id == demo_building_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.building_id == demo_building_id)
        )
        == 1
    )

    # 3. Login as demo_operator and run casual CASH workflow + monthly subscription 0 VND workflow
    op_headers = _login(client, DEMO_OPERATOR_USERNAME, "demo-operator-password-123")
    admin_headers = _login(client, DEMO_ADMIN_USERNAME, "demo-admin-password-123")

    # 3a. Casual vehicle check-in -> duplicate blocked -> preview -> CASH checkout
    casual_in = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": lane_in_id,
            "license_plate": "30A-777.88",
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": std_class_id,
        },
        headers={**op_headers, "Idempotency-Key": f"demo-casual-in-{uuid4()}"},
    )
    assert casual_in.status_code == 201, casual_in.text
    casual_tx_id = UUID(casual_in.json()["transaction"]["id"])

    dup_in = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": lane_in_id,
            "license_plate": "30A77788",
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": std_class_id,
        },
        headers={**op_headers, "Idempotency-Key": f"demo-casual-dup-{uuid4()}"},
    )
    assert dup_in.status_code == 409

    _backdate_checkin(db_session, casual_tx_id, minutes=65)

    preview_casual = client.post(
        "/api/v1/parking/check-out/preview",
        json={"session_id": str(casual_tx_id), "exit_lane_id": lane_out_id},
        headers=op_headers,
    )
    assert preview_casual.status_code == 200, preview_casual.text
    casual_fee = float(preview_casual.json()["fee"])
    assert casual_fee > 0

    out_casual = client.post(
        "/api/v1/parking/check-out",
        json={
            "session_id": str(casual_tx_id),
            "exit_lane_id": lane_out_id,
            "payment_method": "CASH",
            "expected_fee": int(casual_fee),
        },
        headers={**op_headers, "Idempotency-Key": f"demo-casual-out-{casual_tx_id}"},
    )
    assert out_casual.status_code == 200, out_casual.text
    assert out_casual.json()["status"] == "COMPLETED"

    # 3b. Monthly subscription vehicle (30A88888) check-in -> backdate 120 mins -> 0 VND checkout
    monthly_in = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": lane_in_id,
            "license_plate": DEMO_MONTHLY_PLATE,
            "vehicle_type": "CAR",
            "ticket_kind": "MONTHLY",
            "customer_class_id": std_class_id,
        },
        headers={**op_headers, "Idempotency-Key": f"demo-monthly-in-{uuid4()}"},
    )
    assert monthly_in.status_code == 201, monthly_in.text
    monthly_tx_id = UUID(monthly_in.json()["transaction"]["id"])
    _backdate_checkin(db_session, monthly_tx_id, minutes=120)

    preview_monthly = client.post(
        "/api/v1/parking/check-out/preview",
        json={"session_id": str(monthly_tx_id), "exit_lane_id": lane_out_id},
        headers=op_headers,
    )
    assert preview_monthly.status_code == 200, preview_monthly.text
    assert float(preview_monthly.json()["fee"]) == 0.0

    out_monthly = client.post(
        "/api/v1/parking/check-out",
        json={"session_id": str(monthly_tx_id), "exit_lane_id": lane_out_id},
        headers={**op_headers, "Idempotency-Key": f"demo-monthly-out-{monthly_tx_id}"},
    )
    assert out_monthly.status_code == 200, out_monthly.text
    assert out_monthly.json()["status"] == "COMPLETED"
    assert float(out_monthly.json()["fee"]) == 0.0

    # Verify M5 cash shift report for DEMO-BUILDING counts 2 exits (1 casual + 1 monthly)
    shift_start = (datetime.now(UTC) - timedelta(hours=4)).isoformat()
    shift_end = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    shift_res = client.get(
        "/api/v1/m5/cash-shifts",
        params={"building_id": str(demo_building_id), "start": shift_start, "end": shift_end},
        headers=admin_headers,
    )
    assert shift_res.status_code == 200, shift_res.text
    shift_data = shift_res.json()
    assert int(shift_data["exits"]) == 2
    assert int(shift_data["cash_revenue_vnd"]) == int(casual_fee)


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="PostgreSQL concurrent checkout race test requires TEST_POSTGRES_URL",
)
def test_build_01_postgres_concurrent_checkout_race_is_atomic(client, db_session):
    headers = _login(client, "operator", "operator-test-password")
    in_lane_id, out_lane_id = _get_lanes(client, headers)

    res_in = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": in_lane_id, "license_plate": "30A-999.01", "vehicle_type": "CAR"},
        headers={**headers, "Idempotency-Key": f"in-race-{uuid4()}"},
    )
    assert res_in.status_code == 201
    tx_id = UUID(res_in.json()["transaction"]["id"])
    _backdate_checkin(db_session, tx_id, minutes=65)

    def _attempt(idx: int) -> int:
        r = client.post(
            "/api/v1/parking/check-out",
            json={
                "session_id": str(tx_id),
                "exit_lane_id": out_lane_id,
                "payment_method": "CASH",
            },
            headers={**headers, "Idempotency-Key": f"race-co-{idx}-{uuid4()}"},
        )
        return r.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(_attempt, [1, 2]))

    assert 200 in statuses
    db_session.expire_all()
    inv_count = db_session.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.transaction_id == tx_id)
    )
    assert inv_count == 1
    counter = db_session.scalar(
        select(ParkingCounter).where(
            ParkingCounter.building_id == DEFAULT_BUILDING_ID,
            ParkingCounter.vehicle_type == "CAR",
        )
    )
    assert counter is not None and counter.occupied == 0
