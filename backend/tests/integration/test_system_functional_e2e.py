"""Full API -> migrated DB -> ledger/report acceptance, plus PostgreSQL races."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.modules.audit_logs.models import AuditLog
from app.modules.barriers.models import BarrierEvent
from app.modules.buildings.models import DEFAULT_BUILDING_ID
from app.modules.checkin.counter_models import CounterEvent, ParkingCounter
from app.modules.checkin.models import ParkingTransaction
from app.modules.pricing.models import Invoice, Payment
from scripts.system_gate import business_workflow
from tests.integration import test_e2e_cash_workflow as cash_tests

active_lanes = cash_tests.active_lanes
pricing_setup = cash_tests.pricing_setup


def prepare(pricing_setup, db_session):
    rule = pricing_setup["car_hourly_rule"]
    rule.rule_data = {**rule.rule_data, "free_minutes": 0}
    db_session.commit()


def assert_final_ledger(db, session_id, expected_fee):
    db.expire_all()
    tx = db.get(ParkingTransaction, session_id)
    assert tx.status == "COMPLETED"
    invoices = list(db.scalars(select(Invoice).where(Invoice.transaction_id == session_id)))
    assert len(invoices) == 1
    invoice = invoices[0]
    assert invoice.status == "PAID" and invoice.total_vnd == expected_fee
    payments = list(db.scalars(select(Payment).where(Payment.invoice_id == invoice.id)))
    assert len(payments) == 1
    assert (payments[0].method, payments[0].status, payments[0].amount_vnd) == (
        "CASH",
        "PAID",
        expected_fee,
    )
    events = list(db.scalars(select(CounterEvent).where(CounterEvent.session_id == session_id)))
    assert sorted(e.delta for e in events) == [-1, 1]
    assert (
        db.scalar(
            select(ParkingCounter.occupied).where(
                ParkingCounter.building_id == DEFAULT_BUILDING_ID,
                ParkingCounter.vehicle_type == "CAR",
            )
        )
        == 0
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(BarrierEvent)
            .where(BarrierEvent.session_id == session_id, BarrierEvent.lane_id == tx.exit_lane_id)
        )
        == 1
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.entity_id == str(session_id), AuditLog.action == "CHECKOUT_COMPLETED")
        )
        == 1
    )


@pytest.mark.parametrize("with_detection", [False, True], ids=["manual-outage", "file-upload"])
def test_full_cash_counter_ledger_reports_audit_and_manual_fallback(
    client, db_session, operator_headers, active_lanes, pricing_setup, monkeypatch, with_detection
):
    prepare(pricing_setup, db_session)

    # A provider outage must not block the authenticated manual business workflow.
    def unavailable(*args, **kwargs):
        raise RuntimeError("ALPR unavailable")

    if not with_detection:
        monkeypatch.setattr(client.app.state.alpr_runtime, "detect_and_read", unavailable)
    client.headers.update(operator_headers)
    entry, exit_lane = active_lanes
    evidence = {}
    detection_id = None
    if with_detection:
        import cv2
        import numpy as np

        _, encoded = cv2.imencode(".jpg", np.zeros((64, 128, 3), dtype=np.uint8))
        detected = client.post(
            "/api/v1/alpr/detections",
            data={
                "lane_id": str(entry.id),
                "mode": "final",
                "capture_id": str(uuid4()),
                "input_kind": "IMAGE_UPLOAD",
            },
            files={"image": ("car.jpg", encoded.tobytes(), "image/jpeg")},
        )
        assert detected.status_code == 200, detected.text
        detection_id = detected.json()["detection_id"]
        assert detection_id
    business_workflow(
        client,
        entry={"id": str(entry.id), "building_id": str(entry.building_id)},
        exit_lane={"id": str(exit_lane.id)},
        plate="29A12345",
        customer_class_id=str(pricing_setup["customer_class"].id),
        run_id=uuid4().hex,
        evidence=evidence,
        detection_id=detection_id,
    )
    assert_final_ledger(db_session, UUID(evidence["session_id"]), evidence["fee_vnd"])
    tx = db_session.get(ParkingTransaction, UUID(evidence["session_id"]))
    if with_detection:
        assert tx.source == "OPERATOR_CORRECTED" and str(tx.detection_id) == detection_id
    else:
        assert tx.source == "MANUAL_ENTRY" and tx.detection_id is None
    from zoneinfo import ZoneInfo

    from app.modules.buildings.models import Building
    from app.modules.m5.service import aggregate_day

    day = datetime.now(ZoneInfo(db_session.get(Building, DEFAULT_BUILDING_ID).timezone)).date()
    daily = aggregate_day(db_session, DEFAULT_BUILDING_ID, day)
    assert (daily.entries, daily.exits, daily.revenue) == (1, 1, evidence["fee_vnd"])


@pytest.mark.parametrize("same_key", [True, False], ids=["same-key", "different-keys"])
def test_postgres_two_concurrent_cash_checkouts(
    client, db_session, operator_headers, active_lanes, pricing_setup, same_key
):
    if db_session.bind.dialect.name != "postgresql":
        pytest.skip("Requires TEST_POSTGRES_URL; SQLite cannot prove row-lock behavior")
    prepare(pricing_setup, db_session)
    entry, exit_lane = active_lanes
    created = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": uuid4().hex},
        json={
            "lane_id": str(entry.id),
            "license_plate": "29A99999",
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": str(pricing_setup["customer_class"].id),
        },
    )
    assert created.status_code == 201, created.text
    session_id = UUID(created.json()["transaction"]["id"])
    tx = db_session.get(ParkingTransaction, session_id)
    tx.check_in_time = datetime.now(UTC) - timedelta(minutes=30)
    db_session.commit()
    payload = {
        "session_id": str(session_id),
        "exit_lane_id": str(exit_lane.id),
        "payment_method": "CASH",
        "expected_fee": 10000,
    }
    key = uuid4().hex
    ready = Barrier(2)

    def checkout(index):
        ready.wait(timeout=10)
        return client.post(
            "/api/v1/parking/check-out",
            json=payload,
            headers={**operator_headers, "Idempotency-Key": key if same_key else f"{key}-{index}"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(checkout, index) for index in range(2)]
        responses = [future.result(timeout=30) for future in futures]
    assert sorted(r.status_code for r in responses) == ([200, 200] if same_key else [200, 409]), [
        r.text for r in responses
    ]
    if same_key:
        assert responses[0].json()["payment_id"] == responses[1].json()["payment_id"]
    assert_final_ledger(db_session, session_id, 10000)
