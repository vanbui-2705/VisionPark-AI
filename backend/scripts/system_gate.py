"""Real FILE_UPLOAD functional acceptance. Never an ALPR accuracy benchmark.

Writes acceptance transactions through the deployed API. Run on a dedicated,
quiet acceptance building with nonzero CASH pricing; never on production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
from pathlib import Path
from uuid import uuid4

import cv2
import httpx
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"


class ExitCode(IntEnum):
    PASS = 0
    FAIL = 1
    HOLD = 2


class GateFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise GateFailure(message)


def aggregate_status(checks):
    statuses = {GateStatus(check["status"]) for check in checks}
    if GateStatus.FAIL in statuses:
        return GateStatus.FAIL
    if not statuses or GateStatus.HOLD in statuses:
        return GateStatus.HOLD
    return GateStatus.PASS


def _git_commit():
    supplied = os.getenv("GATE_COMMIT") or os.getenv("GITHUB_SHA")
    if supplied:
        return supplied
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def request_json(client, method, path, expected=200, **kwargs):
    response = client.request(method, path, **kwargs)
    # Do not put credentials, tokens, arbitrary server bodies or URLs in reports.
    require(
        response.status_code == expected,
        f"{method} {path}: HTTP {response.status_code}, expected {expected}",
    )
    return response.json()


def _media_bytes(path, *, video_time_ms=0):
    if not path.is_file():
        raise FileNotFoundError(path.name)
    if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        body = path.read_bytes()
        require(
            cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_COLOR) is not None,
            "Acceptance image cannot be decoded",
        )
        return body, "IMAGE_UPLOAD", "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    require(path.suffix.lower() == ".mp4", "Acceptance video must be MP4")
    capture = cv2.VideoCapture(str(path))
    try:
        capture.set(cv2.CAP_PROP_POS_MSEC, video_time_ms)
        success, frame = capture.read()
        require(success and frame is not None, "Acceptance MP4 frame cannot be decoded")
        success, buffer = cv2.imencode(".jpg", frame)
        require(success, "Acceptance frame cannot be encoded")
        return buffer.tobytes(), "VIDEO_FRAME", "image/jpeg"
    finally:
        capture.release()


def business_workflow(
    client, *, entry, exit_lane, plate, customer_class_id, run_id, evidence, detection_id=None
):
    """Exercise real API state; also reusable against the migrated integration app."""
    building = entry["building_id"]
    params = {"building_id": building}
    window = {
        **params,
        "start": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "end": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }

    def occupied():
        rows = request_json(client, "GET", "/api/v1/parking/availability", params=params)
        return next((row["occupied"] for row in rows if row["vehicle_type"] == "CAR"), 0)

    before_counter = occupied()
    before_dashboard = request_json(client, "GET", "/api/v1/m5/dashboard", params=params)
    before_report = request_json(client, "GET", "/api/v1/m5/cash-shifts", params=window)
    payload = {
        "lane_id": entry["id"],
        "license_plate": plate,
        "vehicle_type": "CAR",
        "ticket_kind": "HOURLY",
        "customer_class_id": customer_class_id,
        "source": "OPERATOR_CORRECTED" if detection_id else "MANUAL_ENTRY",
    }
    if detection_id:
        payload["detection_id"] = detection_id
    headers = {"Idempotency-Key": f"{run_id}-in"}
    created = request_json(
        client, "POST", "/api/v1/parking/check-in", expected=201, json=payload, headers=headers
    )["transaction"]
    evidence.update(session_id=created["id"], checkin_key=headers["Idempotency-Key"])
    require(created["status"] == "PARKED", "Check-in is not PARKED")
    require(occupied() == before_counter + 1, "Check-in counter did not increase once")
    replay = request_json(
        client, "POST", "/api/v1/parking/check-in", expected=201, json=payload, headers=headers
    )
    require(replay["transaction"]["id"] == created["id"], "Check-in replay changed session")
    duplicate = client.post(
        "/api/v1/parking/check-in", json=payload, headers={"Idempotency-Key": f"{run_id}-duplicate"}
    )
    require(duplicate.status_code == 409, "Duplicate active plate was not rejected")
    require(occupied() == before_counter + 1, "Replay/duplicate changed counter")
    lookup = {"session_id": created["id"], "exit_lane_id": exit_lane["id"]}
    preview = request_json(client, "POST", "/api/v1/parking/check-out/preview", json=lookup)
    require(preview["status"] == "PARKED", "Preview mutated session status")
    require(
        preview["fee"] > 0,
        "Acceptance tariff must charge nonzero CASH immediately (free_minutes=0)",
    )
    require(occupied() == before_counter + 1, "Preview changed counter")
    checkout = {**lookup, "payment_method": "CASH", "expected_fee": int(preview["fee"])}
    headers = {"Idempotency-Key": f"{run_id}-out"}
    evidence["checkout_key"] = headers["Idempotency-Key"]
    done = request_json(client, "POST", "/api/v1/parking/check-out", json=checkout, headers=headers)
    require(done["status"] == "COMPLETED", "CASH checkout is not complete")
    require(done["fee"] == preview["fee"], "Checkout fee differs from preview")
    require(done.get("barrier_event_recorded") is True, "Missing barrier business event")
    require(bool(done.get("barrier_mode")), "Missing adapter barrier mode")
    evidence.update(
        invoice_id=done.get("invoice_id"),
        payment_id=done.get("payment_id"),
        barrier_mode=done["barrier_mode"],
        fee_vnd=done["fee"],
    )
    require(bool(done.get("invoice_id") and done.get("payment_id")), "Missing CASH ledger IDs")
    again = request_json(
        client, "POST", "/api/v1/parking/check-out", json=checkout, headers=headers
    )
    require(
        all(
            again.get(key) == done.get(key) for key in ("invoice_id", "payment_id", "fee", "status")
        ),
        "Checkout replay changed ledger",
    )
    persisted = request_json(client, "GET", f"/api/v1/parking/transactions/{created['id']}")
    require(persisted["status"] == "COMPLETED", "Persisted session is not complete")
    require(
        persisted.get("detection_id") == detection_id, "Persisted detection provenance mismatch"
    )
    if detection_id is None:
        require(persisted["source"] == "MANUAL_ENTRY", "Manual fallback provenance mismatch")
    invoice = request_json(client, "GET", f"/api/v1/invoices/{done['invoice_id']}")
    payment = request_json(client, "GET", f"/api/v1/payments/{done['payment_id']}")
    require(
        invoice["transaction_id"] == created["id"]
        and invoice["status"] == "PAID"
        and invoice["total_vnd"] == preview["fee"],
        "Invoice mismatch",
    )
    require(
        payment["invoice_id"] == invoice["id"]
        and payment["method"] == "CASH"
        and payment["status"] == "PAID"
        and payment["amount_vnd"] == invoice["total_vnd"],
        "Payment mismatch",
    )
    require(occupied() == before_counter, "Checkout/replay counter drift")
    dashboard = request_json(client, "GET", "/api/v1/m5/dashboard", params=params)
    require(dashboard["parked"] == before_dashboard["parked"], "Dashboard parked count drift")
    report = request_json(client, "GET", "/api/v1/m5/cash-shifts", params=window)
    require(report["entries"] == before_report["entries"] + 1, "Report entries mismatch")
    require(report["exits"] == before_report["exits"] + 1, "Report exits mismatch")
    require(
        report["cash_revenue_vnd"] == before_report["cash_revenue_vnd"] + invoice["total_vnd"],
        "Report CASH ledger mismatch",
    )
    audit = request_json(
        client, "GET", "/api/v1/audit-logs/", params={"resource_id": created["id"], "limit": 100}
    )
    require(
        {"CREATE_CHECKIN", "CHECKOUT_COMPLETED"}.issubset({row["action"] for row in audit}),
        "Missing check-in/checkout audit",
    )
    evidence["checks"] = [
        "checkin",
        "duplicate",
        "preview",
        "cash",
        "idempotency",
        "invoice",
        "payment",
        "counter",
        "dashboard",
        "report",
        "audit",
    ]


def run_system_gate(*, backend_url, frontend_url, image_path, video_path, video_time_ms):
    checks = []
    report = {
        "schema_version": 2,
        "gate": "SYSTEM_FUNCTIONAL",
        "operating_mode": "FILE_UPLOAD",
        "alpr_accuracy": "NOT_EVALUATED",
        "live_camera_rtsp": "NOT_INTEGRATED",
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": _git_commit(),
        "environment": {
            "name": os.getenv("GATE_ENVIRONMENT", "unspecified"),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "run_id": uuid4().hex,
        "checks": checks,
    }

    def check(name, callback):
        item = {"name": name, "status": GateStatus.FAIL}
        checks.append(item)
        try:
            callback(item)
            item["status"] = GateStatus.PASS
            return True
        except (httpx.RequestError, FileNotFoundError):
            item.update(status=GateStatus.HOLD, reason="Required runtime/media unavailable")
        except GateFailure as exc:
            item["reason"] = str(exc)
        except Exception as exc:
            item["reason"] = f"Invalid response or check error: {type(exc).__name__}"
        return False

    with httpx.Client(base_url=backend_url.rstrip("/"), timeout=120) as client:

        def health(item):
            live = request_json(client, "GET", "/health/live")
            require(live.get("status") == "alive", "API is not alive")
            body = request_json(client, "GET", "/health/ready")
            require(
                body.get("database", {}).get("status") == "ready"
                and body["database"].get("provider") == "postgresql",
                "PostgreSQL is not ready",
            )
            require(
                body.get("alpr", {}).get("provider") == "real"
                and body["alpr"].get("status") == "ready"
                and body["alpr"].get("ocr_enabled") is True,
                "Real OCR runtime is not ready",
            )
            item["version"] = body.get("version")

        healthy = check("database_api_runtime", health)

        def frontend(item):
            response = httpx.get(frontend_url.rstrip("/") + "/health/live", timeout=10)
            require(
                response.status_code == 200 and response.json().get("status") == "alive",
                "Frontend health invalid",
            )
            page = httpx.get(frontend_url.rstrip("/") + "/", timeout=10)
            require(
                page.status_code == 200 and 'id="root"' in page.text, "Frontend app unavailable"
            )

        check("frontend_health", frontend)
        media = []

        def acceptance(item):
            require(video_time_ms >= 0, "Video offset must be nonnegative")
            if image_path is None or video_path is None:
                raise FileNotFoundError("Both --image and --video required")
            require(
                image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}, "Expected JPEG/PNG image"
            )
            require(video_path.suffix.lower() == ".mp4", "Expected MP4 video")
            for path in (image_path, video_path):
                media.append(_media_bytes(path, video_time_ms=video_time_ms))
            item["sha256"] = [
                hashlib.sha256(p.read_bytes()).hexdigest() for p in (image_path, video_path)
            ]

        media_ok = check("acceptance_media", acceptance)
        required = [
            "GATE_USERNAME",
            "GATE_PASSWORD",
            "GATE_IN_LANE_ID",
            "GATE_OUT_LANE_ID",
            "GATE_CUSTOMER_CLASS_ID",
            "GATE_PLATE",
            "GATE_ENVIRONMENT",
        ]
        missing = [name for name in required if not os.getenv(name)]
        if missing or report["commit"] == "unknown":
            checks.append(
                {
                    "name": "acceptance_configuration",
                    "status": GateStatus.HOLD,
                    "reason": "Set "
                    + ", ".join(
                        missing + (["GATE_COMMIT"] if report["commit"] == "unknown" else [])
                    ),
                }
            )
        elif healthy and media_ok:

            def workflow(item):
                token = request_json(
                    client,
                    "POST",
                    "/api/v1/auth/login",
                    json={
                        "username": os.environ["GATE_USERNAME"],
                        "password": os.environ["GATE_PASSWORD"],
                    },
                )
                client.headers["Authorization"] = f"Bearer {token['access_token']}"
                lanes = request_json(client, "GET", "/api/v1/lanes/active")
                entry = next(row for row in lanes if row["id"] == os.environ["GATE_IN_LANE_ID"])
                exit_lane = next(
                    row for row in lanes if row["id"] == os.environ["GATE_OUT_LANE_ID"]
                )
                require(
                    entry["direction"] == "IN"
                    and exit_lane["direction"] == "OUT"
                    and entry["building_id"] == exit_lane["building_id"],
                    "Invalid acceptance lanes",
                )
                detection_id = None
                for body, kind, mime in media:
                    result = request_json(
                        client,
                        "POST",
                        "/api/v1/alpr/detections",
                        data={
                            "lane_id": entry["id"],
                            "mode": "final" if kind == "IMAGE_UPLOAD" else "preview",
                            "capture_id": str(uuid4()),
                            "input_kind": kind,
                            "video_time_ms": str(video_time_ms),
                        },
                        files={
                            "image": (
                                "acceptance.png" if mime == "image/png" else "acceptance.jpg",
                                body,
                                mime,
                            )
                        },
                    )
                    require(
                        result.get("provider") == "ultralytics-paddleocr",
                        "Unexpected ALPR provider",
                    )
                    if kind == "IMAGE_UPLOAD":
                        detection_id = result.get("detection_id")
                        require(bool(detection_id), "Final image was not persisted")
                    else:
                        require(
                            result.get("detection_id") is None,
                            "Video preview persisted a detection",
                        )
                business_workflow(
                    client,
                    entry=entry,
                    exit_lane=exit_lane,
                    plate=os.environ["GATE_PLATE"],
                    customer_class_id=os.environ["GATE_CUSTOMER_CLASS_ID"],
                    run_id=report["run_id"],
                    evidence=item,
                    detection_id=detection_id,
                )

            check("file_upload_cash_workflow", workflow)

            # Manual business fallback remains testable even after inference fails.
            def manual(item):
                token = request_json(
                    client,
                    "POST",
                    "/api/v1/auth/login",
                    json={
                        "username": os.environ["GATE_USERNAME"],
                        "password": os.environ["GATE_PASSWORD"],
                    },
                )
                client.headers["Authorization"] = f"Bearer {token['access_token']}"
                lanes = request_json(client, "GET", "/api/v1/lanes/active")
                business_workflow(
                    client,
                    entry=next(r for r in lanes if r["id"] == os.environ["GATE_IN_LANE_ID"]),
                    exit_lane=next(r for r in lanes if r["id"] == os.environ["GATE_OUT_LANE_ID"]),
                    plate="GATE" + report["run_id"][:12].upper(),
                    customer_class_id=os.environ["GATE_CUSTOMER_CLASS_ID"],
                    run_id=report["run_id"] + "-manual",
                    evidence=item,
                )

            check("manual_fallback_without_inference", manual)
        else:
            checks.append(
                {
                    "name": "business_workflows",
                    "status": GateStatus.HOLD,
                    "reason": "Runtime/media prerequisites not met",
                }
            )
    status = aggregate_status(checks)
    report["status"] = status
    return status, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--video-time-ms", type=int, default=0)
    parser.add_argument(
        "--report", type=Path, default=BACKEND_DIR / "var/reports/system-functional-gate.json"
    )
    args = parser.parse_args()
    try:
        status, report = run_system_gate(
            backend_url=args.backend_url,
            frontend_url=args.frontend_url,
            image_path=args.image,
            video_path=args.video,
            video_time_ms=args.video_time_ms,
        )
    except Exception as exc:
        status = GateStatus.FAIL
        report = {
            "gate": "SYSTEM_FUNCTIONAL",
            "status": status,
            "commit": _git_commit(),
            "environment": {"name": os.getenv("GATE_ENVIRONMENT", "unspecified")},
            "alpr_accuracy": "NOT_EVALUATED",
            "error": type(exc).__name__,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": status, "report": str(args.report)}))
    return ExitCode[status.name]


if __name__ == "__main__":
    raise SystemExit(main())
