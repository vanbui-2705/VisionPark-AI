from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.modules.checkin.lifecycle_models import (
    ActorType,
    LifecycleEvent,
    LifecycleEventType,
)
from app.modules.checkin.lifecycle_service import record_lifecycle_event
from app.modules.checkin.models import (
    CheckInSource,
    ParkingTransaction,
    TransactionStatus,
    VehicleType,
)
from app.modules.lanes.models import Lane
from app.modules.users.models import User


def test_record_lifecycle_event_direct(db_session):
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))
    operator = db_session.scalar(select(User).where(User.username == "operator"))

    tx = ParkingTransaction(
        id=uuid4(),
        lane_id=lane.id,
        license_plate="30A11111",
        normalized_plate="30A11111",
        vehicle_type=VehicleType.CAR,
        status=TransactionStatus.PARKED,
        source=CheckInSource.AI_ACCEPTED,
        idempotency_key="direct-lc-1",
        request_fingerprint="1" * 64,
    )
    db_session.add(tx)
    db_session.flush()

    event = record_lifecycle_event(
        session=db_session,
        session_id=tx.id,
        event_type=LifecycleEventType.CHECKED_IN,
        actor_type=ActorType.OPERATOR,
        actor_id=operator.id,
        lane_id=lane.id,
        details={"sample": "data"},
        image_ref="/media/sample.jpg",
    )
    db_session.commit()

    saved = db_session.scalar(select(LifecycleEvent).where(LifecycleEvent.id == event.id))
    assert saved is not None
    assert saved.session_id == tx.id
    assert saved.event_type == LifecycleEventType.CHECKED_IN
    assert saved.actor_type == ActorType.OPERATOR
    assert saved.actor_id == operator.id
    assert saved.details == {"sample": "data"}
    assert saved.image_ref == "/media/sample.jpg"


def test_checkin_creates_lifecycle_event_atomic(client, db_session, operator_headers):
    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))

    # Perform normal check-in
    payload = {
        "lane_id": str(lane.id),
        "license_plate": "30A22222",
        "source": "MANUAL_ENTRY",
    }
    resp = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": "lc-checkin-key"},
        json=payload,
    )
    assert resp.status_code == 201
    tx_id = UUID(resp.json()["transaction"]["id"])

    events = db_session.scalars(
        select(LifecycleEvent)
        .where(LifecycleEvent.session_id == tx_id)
        .order_by(LifecycleEvent.occurred_at.asc())
    ).all()
    assert len(events) >= 1
    event_types = [e.event_type for e in events]
    assert LifecycleEventType.CHECKED_IN in event_types


def test_checkin_with_operator_corrected_records_event(client, db_session, operator_headers):
    from app.modules.alpr.models import Detection

    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))

    detection = Detection(
        id=uuid4(),
        lane_id=lane.id,
        image_key="lane_corr.jpg",
        raw_plate="30A33333",
        normalized_plate="30A33333",
        confidence=0.95,
    )
    db_session.add(detection)
    db_session.commit()

    # Check-in with corrected plate
    payload = {
        "lane_id": str(lane.id),
        "detection_id": str(detection.id),
        "license_plate": "30A33334",
        "override_reason": "Operator fixed blurry digit",
    }
    resp = client.post(
        "/api/v1/parking/check-in",
        headers={**operator_headers, "Idempotency-Key": "lc-corr-key"},
        json=payload,
    )
    assert resp.status_code == 201
    tx_id = UUID(resp.json()["transaction"]["id"])

    events = db_session.scalars(
        select(LifecycleEvent)
        .where(LifecycleEvent.session_id == tx_id)
        .order_by(LifecycleEvent.occurred_at.asc())
    ).all()
    event_types = [e.event_type for e in events]
    assert LifecycleEventType.OPERATOR_CORRECTED in event_types
    assert LifecycleEventType.CHECKED_IN in event_types

    corr_event = next(e for e in events if e.event_type == LifecycleEventType.OPERATOR_CORRECTED)
    assert corr_event.details["reason"] == "Operator fixed blurry digit"


def test_lifecycle_event_append_only_enforcement(db_session):
    from app.modules.checkin.lifecycle_models import AppendOnlyModelError

    lane = db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))

    tx = ParkingTransaction(
        id=uuid4(),
        lane_id=lane.id,
        license_plate="30A99999",
        normalized_plate="30A99999",
        vehicle_type=VehicleType.CAR,
        status=TransactionStatus.PARKED,
        source=CheckInSource.MANUAL_ENTRY,
        idempotency_key="append-only-test",
        request_fingerprint="9" * 64,
    )
    db_session.add(tx)
    db_session.flush()

    event = record_lifecycle_event(
        session=db_session,
        session_id=tx.id,
        event_type=LifecycleEventType.CHECKED_IN,
        actor_type=ActorType.SYSTEM,
    )
    db_session.commit()

    # Attempt to update should raise AppendOnlyModelError
    event.details = {"tampered": True}
    with pytest.raises(AppendOnlyModelError):
        db_session.commit()
    db_session.rollback()

    # Attempt to delete should raise AppendOnlyModelError
    db_session.delete(event)
    with pytest.raises(AppendOnlyModelError):
        db_session.commit()
    db_session.rollback()
