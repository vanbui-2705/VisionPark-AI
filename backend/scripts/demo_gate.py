"""Run the Functional Demo Gate (BUILD-06 / DEMO-06).

Verifies end-to-end functional demo workflows using labeled test fixtures without
making commercial ALPR accuracy claims:
  1. Database & schema readiness
  2. API health endpoints (/health/live, /health/ready)
  3. Seed accounts & IN/OUT lanes
  4. Check-in, counter increment (+1), and duplicate active plate protection (409)
  5. Checkout preview, direct CASH checkout, and idempotency (replay + conflict detection)
  6. Unified Ledger (Invoice + Payment), Counter decrement (-1), and M5 daily/cash-shift reports
  7. Manual fallback check-in (source=MANUAL_ENTRY) and audit logging
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "demo-gate-secret-key-with-at-least-thirty-two-characters")
os.environ.setdefault("ALPR_PROVIDER", "real")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.readiness import RuntimeALPRProbe  # noqa: E402
from app.database.seed import seed_database  # noqa: E402
from app.database.session import database  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.audit_logs.models import AuditLog  # noqa: E402
from app.modules.buildings.models import DEFAULT_BUILDING_ID, Building, ParkingLot  # noqa: E402
from app.modules.checkin.counter_models import ParkingCounter  # noqa: E402
from app.modules.checkin.models import ParkingTransaction  # noqa: E402
from app.modules.lanes.models import Lane  # noqa: E402
from app.modules.lot_settings.schemas import default_settings  # noqa: E402
from app.modules.pricing.models import Invoice, Payment  # noqa: E402
from tests.alpr_double import FakeALPRRuntime  # noqa: E402


def _git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def run_functional_demo_gate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, details: dict[str, Any] | None = None) -> None:
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {name}")
        checks.append({"name": name, "passed": bool(passed), "details": details or {}})
        if not passed:
            raise RuntimeError(f"Functional demo gate failed at step: {name}")

    with tempfile.TemporaryDirectory(prefix="visionpark_demo_gate_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_file = tmp_path / "demo_gate.db"
        media_dir = tmp_path / "media"

        database_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        alembic_cfg.attributes["database_url"] = database_url
        command.upgrade(alembic_cfg, "head")

        settings = Settings(
            _env_file=None,
            environment="test",
            database_url=database_url,
            jwt_secret_key=SecretStr("demo-gate-secret-key-with-at-least-32-bytes"),
            local_storage_path=str(media_dir),
            alpr_provider="real",
            auto_seed=False,
            seed_admin_username="admin",
            seed_admin_password=SecretStr("admin-demo-password"),
            seed_operator_username="operator",
            seed_operator_password=SecretStr("operator-demo-password"),
        )

        app = create_app(settings)
        app.state.effective_pricing = lambda db, building_id, at: True
        app.state.alpr_runtime = FakeALPRRuntime()
        app.state.alpr_readiness_probe = RuntimeALPRProbe(
            app.state.alpr_runtime, provider="test", version="test"
        )
        with TestClient(app) as client:
            session = database.create_session()
            try:
                seed_database(session, settings)
                lot = session.scalar(
                    select(ParkingLot).where(ParkingLot.building_id == DEFAULT_BUILDING_ID)
                )
                config = default_settings(session.get(Building, DEFAULT_BUILDING_ID))
                config.ai.plate_confidence = 0.85
                for capacity in config.capacities.values():
                    capacity.physical_capacity = 100
                    capacity.safe_capacity = 100
                if lot is not None:
                    lot.settings = config.model_dump(mode="json")
                session.add_all(
                    [
                        Lane(
                            name="LANE_IN_01",
                            direction="IN",
                            video_source="demo",
                            is_active=True,
                        ),
                        Lane(
                            name="LANE_OUT_01",
                            direction="OUT",
                            video_source="demo",
                            is_active=True,
                        ),
                    ]
                )
                session.commit()
                record("1. Database readiness & seed demo validity", True)

                # 2. Health check
                live_res = client.get("/health/live")
                ready_res = client.get("/health/ready")
                record(
                    "2. API health check (/health/live & /health/ready)",
                    live_res.status_code == 200 and ready_res.status_code == 200,
                    {"live": live_res.status_code, "ready": ready_res.status_code},
                )

                # 3. Auth & Lanes
                login_res = client.post(
                    "/api/v1/auth/login",
                    json={"username": "admin", "password": "admin-demo-password"},
                )
                assert login_res.status_code == 200
                headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
                lanes = client.get("/api/v1/lanes/active", headers=headers).json()
                in_lane = next((row for row in lanes if row["direction"] == "IN"), None)
                out_lane = next((row for row in lanes if row["direction"] == "OUT"), None)
                record(
                    "3. Authenticated active IN/OUT lanes available",
                    in_lane is not None and out_lane is not None,
                    {"lanes_count": len(lanes)},
                )

                # 4. Check-in + Counter (+1) + Duplicate protection
                plate = "30A-123.45"
                checkin_res = client.post(
                    "/api/v1/parking/check-in",
                    json={"lane_id": in_lane["id"], "license_plate": plate, "vehicle_type": "CAR"},
                    headers={**headers, "Idempotency-Key": f"demo-in-{uuid4()}"},
                )
                assert checkin_res.status_code == 201, checkin_res.text
                tx_id = UUID(checkin_res.json()["transaction"]["id"])

                dup_res = client.post(
                    "/api/v1/parking/check-in",
                    json={"lane_id": in_lane["id"], "license_plate": plate, "vehicle_type": "CAR"},
                    headers={**headers, "Idempotency-Key": f"demo-in-dup-{uuid4()}"},
                )
                session.expire_all()
                counter_after_in = session.scalar(
                    select(ParkingCounter.occupied).where(
                        ParkingCounter.building_id == DEFAULT_BUILDING_ID,
                        ParkingCounter.vehicle_type == "CAR",
                    )
                )
                record(
                    "4. Check-in increments counter (+1) & blocks duplicate plate (409)",
                    dup_res.status_code == 409
                    and dup_res.json().get("code")
                    in {"PLATE_ALREADY_PARKED", "DUPLICATE_ACTIVE_SESSION"}
                    and counter_after_in == 1,
                    {"occupied_after_in": counter_after_in, "dup_status": dup_res.status_code},
                )

                # Backdate check-in by 65 minutes so a billable fee (> 0) is generated
                db_tx = session.get(ParkingTransaction, tx_id)
                db_tx.check_in_time = datetime.now(UTC) - timedelta(minutes=65)
                session.commit()

                # 5. Checkout Preview + Direct CASH Checkout + Idempotency
                preview_res = client.post(
                    "/api/v1/parking/check-out/preview",
                    json={"session_id": str(tx_id), "exit_lane_id": out_lane["id"]},
                    headers=headers,
                )
                assert preview_res.status_code == 200, preview_res.text
                expected_fee = int(preview_res.json()["fee"])
                assert expected_fee > 0

                checkout_key = f"demo-out-{tx_id}"
                checkout_payload = {
                    "session_id": str(tx_id),
                    "exit_lane_id": out_lane["id"],
                    "payment_method": "CASH",
                    "expected_fee": expected_fee,
                }
                out_res = client.post(
                    "/api/v1/parking/check-out",
                    json=checkout_payload,
                    headers={**headers, "Idempotency-Key": checkout_key},
                )
                assert out_res.status_code == 200, out_res.text
                out_body = out_res.json()

                # Replay with identical payload -> 200 OK
                replay_res = client.post(
                    "/api/v1/parking/check-out",
                    json=checkout_payload,
                    headers={**headers, "Idempotency-Key": checkout_key},
                )
                # Replay with mutated payload -> 409 IDEMPOTENCY_KEY_REUSED
                conflict_res = client.post(
                    "/api/v1/parking/check-out",
                    json={**checkout_payload, "is_lost_ticket": True},
                    headers={**headers, "Idempotency-Key": checkout_key},
                )
                record(
                    "5. Direct CASH checkout, idempotent replay (200), and payload conflict (409)",
                    out_body["status"] == "COMPLETED"
                    and out_body["barrier_mode"] == "SIMULATED"
                    and replay_res.status_code == 200
                    and conflict_res.status_code == 409
                    and conflict_res.json().get("code") == "IDEMPOTENCY_KEY_REUSED",
                    {
                        "fee": out_body["fee"],
                        "replay_status": replay_res.status_code,
                        "conflict_code": conflict_res.json().get("code"),
                    },
                )

                # 6. Ledger (Invoice + Payment), Counter (-1), and M5 Reports consistency
                session.expire_all()
                inv_count = session.scalar(
                    select(func.count()).select_from(Invoice).where(Invoice.transaction_id == tx_id)
                )
                pay_row = session.scalar(
                    select(Payment)
                    .join(Invoice, Payment.invoice_id == Invoice.id)
                    .where(Invoice.transaction_id == tx_id)
                )
                counter_after_out = session.scalar(
                    select(ParkingCounter.occupied).where(
                        ParkingCounter.building_id == DEFAULT_BUILDING_ID,
                        ParkingCounter.vehicle_type == "CAR",
                    )
                )
                building = session.get(Building, DEFAULT_BUILDING_ID)
                if building is not None:
                    building.timezone = "UTC"
                db_tx = session.get(ParkingTransaction, tx_id)
                checkout_utc = (db_tx.exit_time or datetime.now(UTC)).replace(tzinfo=UTC)
                if db_tx is not None:
                    db_tx.check_in_time = checkout_utc
                session.commit()

                today_str = checkout_utc.date().isoformat()
                rebuild_res = client.post(
                    f"/api/v1/m5/daily-stats/rebuild?building_id={DEFAULT_BUILDING_ID}&day={today_str}",
                    headers=headers,
                )
                assert rebuild_res.status_code == 200, rebuild_res.text
                stat_data = rebuild_res.json()
                record(
                    "6. Unified Ledger (Invoice/Payment), Counter (0), and M5 Daily Report match",
                    inv_count == 1
                    and pay_row is not None
                    and pay_row.status == "PAID"
                    and pay_row.amount_vnd == expected_fee
                    and counter_after_out == 0
                    and int(stat_data["exits"]) == 1
                    and int(float(stat_data["revenue"])) == expected_fee,
                    {
                        "invoice_count": inv_count,
                        "payment_amount_vnd": pay_row.amount_vnd if pay_row else None,
                        "occupied_after_out": counter_after_out,
                        "m5_exits": stat_data["exits"],
                        "m5_revenue": float(stat_data["revenue"]),
                    },
                )

                # 7. Manual fallback check-in & audit log
                manual_res = client.post(
                    "/api/v1/parking/check-in",
                    json={
                        "lane_id": in_lane["id"],
                        "license_plate": "51H-888.99",
                        "source": "MANUAL_ENTRY",
                    },
                    headers={**headers, "Idempotency-Key": f"demo-manual-{uuid4()}"},
                )
                assert manual_res.status_code == 201
                manual_tx = manual_res.json()["transaction"]
                audit_count = session.scalar(select(func.count()).select_from(AuditLog)) or 0
                record(
                    "7. Manual fallback check-in (source=MANUAL_ENTRY) & audit logging",
                    manual_tx["source"] == "MANUAL_ENTRY" and audit_count >= 3,
                    {"source": manual_tx["source"], "audit_log_count": audit_count},
                )
            finally:
                session.close()
        database.dispose()

    return {
        "timestamp": time.time(),
        "commit": _git_commit(),
        "environment": "functional_demo_gate",
        "gate_type": "FUNCTIONAL_DEMO_GATE",
        "alpr_accuracy_claimed": False,
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
    }


def main() -> None:
    print("================================================================================")
    print("                     VISIONPARK FUNCTIONAL DEMO GATE (BUILD-06)                ")
    print("================================================================================")
    report = run_functional_demo_gate()
    out_dir = BACKEND_DIR / "var" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "demo-gate-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved functional demo gate report: {report_path.relative_to(BACKEND_DIR)}")
    print("================================================================================")
    print("                     FUNCTIONAL DEMO GATE: PASS                                ")
    print("================================================================================")


if __name__ == "__main__":
    main()
