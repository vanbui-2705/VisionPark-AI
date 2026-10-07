from uuid import uuid4

from sqlalchemy import select

from app.modules.checkin.models import CheckInSource, ParkingTransaction
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
    assert data["lane_snapshot_name"] == lane.name
    assert data["lane_snapshot_direction"] == lane.direction

    # Change lane name in DB
    lane.name = "CHANGED_LANE"
    db_session.commit()

    # Read history - snapshot should remain unchanged
    history = client.get(f"/api/v1/parking/transactions/{data['id']}", headers=operator_headers)
    assert history.status_code == 200
    assert history.json()["lane_snapshot_name"] == "LANE_IN_01"  # Kept the snapshot
