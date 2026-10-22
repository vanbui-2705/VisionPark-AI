from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.checkin.models import (
    CheckInSource,
    ParkingTransaction,
    TransactionStatus,
    VehicleType,
)
from app.modules.lanes.models import Lane
from app.modules.users.models import User


def test_pagination_and_audit_with_200_records(client, db_session, operator_headers):
    # Seed 250 records
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))
    operator = db_session.scalar(select(User).where(User.username == "operator"))

    records = []
    for i in range(250):
        records.append(
            ParkingTransaction(
                id=uuid4(),
                lane_id=lane.id,
                lane_snapshot_name=lane.name,
                lane_snapshot_direction=lane.direction,
                license_plate=f"29A{i:05d}",
                normalized_plate=f"29A{i:05d}",
                status="COMPLETED",  # Not parked to avoid active conflict
                check_in_operator_id=operator.id,
                operator_snapshot_name=operator.display_name,
                source=CheckInSource.MANUAL_ENTRY,
                is_manual_override=True,
                idempotency_key=f"bulk-{i}",
                request_fingerprint="a" * 64,
            )
        )
    db_session.add_all(records)
    db_session.commit()

    # Test Pagination in transactions
    response = client.get("/api/v1/parking/transactions?limit=100&page=0", headers=operator_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 250
    assert len(data["data"]) == 100
    assert data["page"] == 0
    assert data["limit"] == 100

    response2 = client.get(
        "/api/v1/parking/transactions?limit=100&page=2", headers=operator_headers
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["data"]) >= 50
    assert data2["page"] == 2


def test_provenance_locking_and_snapshot(client, db_session, operator_headers):
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))

    # Send check-in without detection (client sends original_ai_plate - should be ignored)
    payload = {
        "lane_id": str(lane.id),
        "license_plate": "30A12345",
        "original_ai_plate": "30A12345",  # Should be ignored because no detection
        "confidence": 0.99,  # Should be ignored
        "source": "AI_ACCEPTED",  # Should be overridden to MANUAL_ENTRY
    }

    response = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": "prov-test"},
        json=payload,
    )
    assert response.status_code == 201

    data = response.json()["transaction"]
    assert data["source"] == "MANUAL_ENTRY"
    assert data["original_ai_plate"] is None
    assert data["confidence"] is None
    assert data["lane_name"] == lane.name
    assert data["lane_direction"] == lane.direction

    # Change lane name in DB
    lane.name = "CHANGED_LANE"
    db_session.commit()

    # Read history - snapshot should remain unchanged
    history = client.get(f"/api/v1/parking/transactions/{data['id']}", headers=operator_headers)
    assert history.status_code == 200
    assert history.json()["lane_name"] == "LANE_IN_01"  # Kept the snapshot


def test_phase3_session_schema_expansion(client, db_session, operator_headers):
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))
    operator = db_session.scalar(select(User).where(User.username == "operator"))

    # Test creating a session without plate (e.g. bicycle) and with new status and fields
    tx = ParkingTransaction(
        id=uuid4(),
        lane_id=lane.id,
        license_plate=None,
        normalized_plate=None,
        ticket_code="TC-BIKE-001",
        vehicle_type=VehicleType.BICYCLE,
        status=TransactionStatus.ENTERED,
        fee=5000.0,
        price_snapshot={"base_rate": 5000, "vehicle_type": "BICYCLE"},
        check_in_operator_id=operator.id,
        source=CheckInSource.MANUAL_ENTRY,
        idempotency_key="tx-bike-01",
        request_fingerprint="b" * 64,
    )
    db_session.add(tx)
    db_session.commit()

    # Query through API
    resp = client.get(f"/api/v1/parking/transactions/{tx.id}", headers=operator_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["license_plate"] is None
    assert body["normalized_plate"] is None
    assert body["ticket_code"] == "TC-BIKE-001"
    assert body["vehicle_type"] == "BICYCLE"
    assert body["status"] == "ENTERED"
    assert body["fee"] == 5000.0


def test_phase3_active_ticket_code_unique(db_session):
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))

    tx1 = ParkingTransaction(
        id=uuid4(),
        lane_id=lane.id,
        license_plate=None,
        normalized_plate=None,
        ticket_code="TC-DUP-999",
        vehicle_type=VehicleType.BICYCLE,
        status=TransactionStatus.PARKED,
        source=CheckInSource.MANUAL_ENTRY,
        idempotency_key="dup-key-1",
        request_fingerprint="c" * 64,
    )
    db_session.add(tx1)
    db_session.commit()

    # Duplicate active ticket_code must fail with IntegrityError
    tx2 = ParkingTransaction(
        id=uuid4(),
        lane_id=lane.id,
        license_plate=None,
        normalized_plate=None,
        ticket_code="TC-DUP-999",
        vehicle_type=VehicleType.BICYCLE,
        status=TransactionStatus.ENTERED,
        source=CheckInSource.MANUAL_ENTRY,
        idempotency_key="dup-key-2",
        request_fingerprint="d" * 64,
    )
    db_session.add(tx2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
