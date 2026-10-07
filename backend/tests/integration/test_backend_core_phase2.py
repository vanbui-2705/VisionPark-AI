import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.database.idempotency import fingerprint_payload
from app.modules.alpr.models import Detection
from app.modules.audit_logs.models import AuditLog
from app.modules.checkin.models import ParkingTransaction
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.lanes.models import Lane
from app.modules.users.models import Role, User
from tests.conftest import BACKEND_ROOT, TEST_JWT_SECRET, login, make_alembic_config

PHASE2_PARENT = "20261004_0005"


@pytest.fixture
def in_lane(db_session):
    return db_session.scalar(select(Lane).where(Lane.name == "LANE_IN_01"))


def check_in(client, headers, lane, key="phase2-key", **fields):
    return client.post(
        "/api/v1/parking/check-in",
        headers={**headers, "Idempotency-Key": key},
        json={"lane_id": str(lane.id), "license_plate": "29A12345", **fields},
    )


@pytest.mark.parametrize("path", ["/api/v1/lanes/", "/api/v1/lanes/active", "detail"])
def test_operator_can_read_lanes_for_station_but_auth_is_required(
    client, operator_headers, in_lane, path
):
    if path == "detail":
        path = f"/api/v1/lanes/{in_lane.id}"
    assert client.get(path, headers=operator_headers).status_code == 200
    assert client.get(path).status_code == 401


def test_retry_does_not_duplicate_transaction_or_audit(
    client, db_session, operator_headers, in_lane
):
    first = check_in(client, operator_headers, in_lane, override_reason="manual confirmation")
    second = check_in(client, operator_headers, in_lane, override_reason="manual confirmation")
    assert first.status_code == second.status_code == 201
    assert first.json()["transaction"] == second.json()["transaction"]
    assert db_session.scalar(select(func.count()).select_from(ParkingTransaction)) == 1
    assert (
        db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "CREATE_CHECKIN")
        )
        == 1
    )


def test_changed_notes_conflict_instead_of_silent_replay(client, operator_headers, in_lane):
    assert (
        check_in(client, operator_headers, in_lane, override_reason="accepted").status_code == 201
    )
    changed = check_in(client, operator_headers, in_lane, override_reason="different reason")
    assert changed.status_code == 409
    assert changed.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert changed.headers["X-Correlation-ID"] == changed.json()["correlation_id"]


def test_idempotency_key_cannot_replay_another_actor(client, operator_headers, in_lane):
    assert check_in(client, operator_headers, in_lane).status_code == 201
    token = login(client, "admin", "admin-test-password")["access_token"]
    changed = check_in(client, {"Authorization": f"Bearer {token}"}, in_lane)
    assert changed.status_code == 409
    assert changed.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_successful_retry_survives_lane_deactivation(client, db_session, operator_headers, in_lane):
    first = check_in(client, operator_headers, in_lane)
    in_lane.is_active = False
    db_session.commit()
    retried = check_in(client, operator_headers, in_lane)
    assert first.status_code == retried.status_code == 201
    assert first.json()["transaction"] == retried.json()["transaction"]
    new_request = check_in(
        client, operator_headers, in_lane, key="new-key", license_plate="30A12345"
    )
    assert new_request.status_code == 400
    assert new_request.json()["code"] == "LANE_INACTIVE"


@pytest.mark.parametrize(
    "key,code", [(" " * 3, "IDEMPOTENCY_KEY_REQUIRED"), ("k" * 256, "INVALID_IDEMPOTENCY_KEY")]
)
def test_invalid_header_key_is_rejected_before_database_write(
    client, db_session, operator_headers, in_lane, key, code
):
    result = check_in(client, operator_headers, in_lane, key=key)
    assert result.status_code == 422
    assert result.json()["code"] == code
    assert db_session.scalar(select(func.count()).select_from(ParkingTransaction)) == 0


def test_conflicting_header_and_body_keys_are_rejected(client, operator_headers, in_lane):
    result = check_in(client, operator_headers, in_lane, idempotency_key="body-key")
    assert result.status_code == 422
    assert result.json()["code"] == "IDEMPOTENCY_KEY_MISMATCH"


def test_phase2_legacy_fingerprints_can_still_replay(client, db_session, operator_headers, in_lane):
    first = check_in(client, operator_headers, in_lane, override_reason="legacy reason")
    row = db_session.get(ParkingTransaction, UUID(first.json()["transaction"]["id"]))
    row.request_fingerprint = fingerprint_payload(
        {
            "lane_id": in_lane.id,
            "normalized_plate": "29A12345",
            "detection_id": None,
            "source": "MANUAL_ENTRY",
            "ai_plate": None,
            "confidence": None,
        }
    )
    db_session.commit()
    retried = check_in(client, operator_headers, in_lane, override_reason="legacy reason")
    assert retried.status_code == 201
    assert retried.json()["transaction"]["id"] == first.json()["transaction"]["id"]
    changed = check_in(client, operator_headers, in_lane, override_reason="changed legacy reason")
    assert changed.status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "UNKNOWN"),
        ("confidence", 1.1),
        ("idempotency_key", ""),
        ("request_fingerprint", "short"),
    ],
)
def test_database_rejects_invalid_transaction_fields(db_session, in_lane, field, value):
    values = {
        "license_plate": "29A12345",
        "normalized_plate": "29A12345",
        "lane_id": in_lane.id,
        "status": "PARKED",
        "source": "MANUAL_ENTRY",
        "idempotency_key": "db-guard",
        "request_fingerprint": "a" * 64,
    }
    db_session.add(ParkingTransaction(**{**values, field: value}))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(ParkingTransaction)) == 0


def test_additive_migration_and_rollback_preserve_existing_data(database_url):
    config = make_alembic_config(database_url)
    command.upgrade(config, PHASE2_PARENT)
    engine = create_engine(database_url)
    detection_id, transaction_id = uuid4(), uuid4()
    with Session(engine) as session:
        from sqlalchemy import MetaData, Table, Uuid
        old_users = Table("users", MetaData(), autoload_with=engine)
        old_users.c.id.type = Uuid()
        old_users.c.role_id.type = Uuid()
        for role_name in ("ADMIN", "OPERATOR", "ACCOUNTANT", "TECHNICIAN"):
            role = Role(name=role_name)
            session.add(role)
            session.flush()
            if role_name in ("ADMIN", "OPERATOR"):
                session.execute(
                    old_users.insert().values(
                        id=uuid4(),
                        role_id=role.id,
                        username=role_name.lower(),
                        display_name=role_name,
                        password_hash="legacy-hash",
                        is_active=True,
                    )
                )
        lane = Lane(name="LANE_IN_01", direction="IN", video_source="demo.mp4", is_active=True)
        session.add(lane)
        session.flush()
        old_detections = Table("detections", MetaData(), autoload_with=engine)
        old_detections.c.id.type = Uuid()
        old_detections.c.lane_id.type = Uuid()
        session.execute(
            old_detections.insert().values(
                id=detection_id,
                lane_id=lane.id,
                image_key="existing-phase1.jpg",
                requires_confirmation=False,
                is_confirmed=False,
            )
        )
        session.flush()
        from sqlalchemy import text

        session.execute(
            text(
                """
                INSERT INTO parking_transactions (
                    id, lane_id, detection_id, license_plate, normalized_plate, 
                    status, source, idempotency_key, request_fingerprint, is_manual_override
                ) VALUES (
                    :id, :lane, :det, :plate, :norm, 
                    :status, :src, :key, :fp, :is_man
                )
                """
            ),
            {
                "id": transaction_id.hex,
                "lane": lane.id.hex,
                "det": detection_id.hex,
                "plate": "29A12345",
                "norm": "29A12345",
                "status": "PARKED",
                "src": "MANUAL_ENTRY",
                "key": "old-key",
                "fp": "a" * 64,
                "is_man": False,
            },
        )
        session.commit()
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    for revision in ("head",):
        if revision == PHASE2_PARENT:
            command.downgrade(config, revision)
        engine = create_engine(database_url)
        with Session(engine) as session:
            assert session.get(Detection, detection_id).image_key == "existing-phase1.jpg"
            row = session.execute(
                text("SELECT detection_id FROM parking_transactions WHERE id = :id"),
                {"id": transaction_id.hex},
            ).fetchone()
            assert row is not None
            assert row[0].replace("-", "") == detection_id.hex
            assert session.scalar(select(func.count()).select_from(User)) == 2
            assert session.scalar(select(func.count()).select_from(Role)) == 4
        constraints = {
            item["name"] for item in inspect(engine).get_check_constraints("parking_transactions")
        }
        assert ("ck_parking_transactions_status" in constraints) == (revision == "head")
        engine.dispose()
    command.upgrade(config, "head")


def test_bootstrap_twice_from_empty_database_creates_phase2_fixture(database_url):
    environment = {
        **os.environ,
        "DATABASE_URL": database_url,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
        "AUTO_SEED": "true",
        "SEED_ADMIN_PASSWORD": "admin-test-password",
        "SEED_OPERATOR_PASSWORD": "operator-test-password",
        "ALPR_PROVIDER": "real",
    }
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "app.database.bootstrap"],
            cwd=BACKEND_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    engine = create_engine(database_url)
    assert "parking_transactions" in inspect(engine).get_table_names()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Role)) == 4
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Lane)) == 0
    engine.dispose()


@pytest.mark.parametrize("race", ["same-key", "same-plate", "changed-payload"])
def test_postgres_concurrent_requests_are_atomic(
    database_url, client, db_session, operator_headers, in_lane, monkeypatch, race
):
    if not database_url.startswith("postgresql"):
        pytest.skip("Race evidence requires real PostgreSQL")
    gate = Barrier(2)
    original = DatabaseCheckInRepository.get_active_by_plate

    def synchronized_read(repo, plate):
        result = original(repo, plate)
        if result is None:
            gate.wait(timeout=10)
        return result

    monkeypatch.setattr(DatabaseCheckInRepository, "get_active_by_plate", synchronized_read)

    def submit(index):
        key = f"race-{index}" if race == "same-plate" else "race-key"
        notes = f"reason-{index}" if race == "changed-payload" else "race reason"
        return check_in(client, operator_headers, in_lane, key=key, override_reason=notes)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, [0, 1]))
    assert db_session.scalar(select(func.count()).select_from(ParkingTransaction)) == 1
    assert (
        db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "CREATE_CHECKIN")
        )
        == 1
    )
    if race == "same-key":
        assert [result.status_code for result in responses] == [201, 201]
        assert responses[0].json()["transaction"]["id"] == responses[1].json()["transaction"]["id"]
    else:
        assert sorted(result.status_code for result in responses) == [201, 409]
        conflict = next(result for result in responses if result.status_code == 409)
        assert conflict.json()["code"] == (
            "PLATE_ALREADY_PARKED" if race == "same-plate" else "IDEMPOTENCY_KEY_REUSED"
        )


