"""Verify the real VisionPark workflow in FILE_UPLOAD operating mode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

import cv2
import httpx

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


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True, timeout=5
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _run_command(name: str, command: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "name": name,
        "status": GateStatus.PASS if completed.returncode == 0 else GateStatus.FAIL,
        "command": command,
        "returncode": completed.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def _hold(name: str, reason: str) -> dict[str, Any]:
    return {"name": name, "status": GateStatus.HOLD, "reason": reason}


def _fail(name: str, reason: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": GateStatus.FAIL, "reason": reason, **details}


def _pass(name: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": GateStatus.PASS, **details}


def aggregate_status(checks: list[dict[str, Any]]) -> GateStatus:
    statuses = {GateStatus(check["status"]) for check in checks}
    if GateStatus.FAIL in statuses:
        return GateStatus.FAIL
    if GateStatus.HOLD in statuses:
        return GateStatus.HOLD
    return GateStatus.PASS


def _runtime_health(client: httpx.Client) -> dict[str, Any]:
    try:
        response = client.get("/health/ready")
    except httpx.RequestError as exc:
        return _hold("runtime_readiness", f"Backend is not reachable: {exc}")

    try:
        payload = response.json()
    except ValueError:
        return _fail("runtime_readiness", "Backend readiness response is not JSON")

    database = payload.get("database", {})
    alpr = payload.get("alpr", {})
    if response.status_code != 200:
        return _fail(
            "runtime_readiness",
            f"Backend readiness returned HTTP {response.status_code}",
            response=payload,
        )
    if database.get("status") != "ready":
        return _fail("runtime_readiness", "PostgreSQL is not ready", response=payload)
    if alpr.get("provider") != "real" or alpr.get("status") != "ready":
        return _fail(
            "runtime_readiness",
            "The deployed ALPR provider is not the ready real provider",
            response=payload,
        )
    return _pass(
        "runtime_readiness",
        provider=alpr.get("provider"),
        model_version=alpr.get("model_version") or alpr.get("version"),
        ocr_enabled=alpr.get("ocr_enabled"),
    )


def _frontend_health(frontend_url: str) -> dict[str, Any]:
    try:
        response = httpx.get(frontend_url.rstrip("/") + "/health/live", timeout=10)
    except httpx.RequestError as exc:
        return _hold("frontend_health", f"Frontend is not reachable: {exc}")
    if response.status_code != 200:
        return _fail("frontend_health", f"Frontend health returned HTTP {response.status_code}")
    return _pass("frontend_health", url=str(response.url))


def _media_bytes(path: Path, *, video_time_ms: int = 0) -> tuple[bytes, str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return path.read_bytes(), "IMAGE_UPLOAD", media_type

    capture = cv2.VideoCapture(str(path))
    try:
        if video_time_ms > 0:
            capture.set(cv2.CAP_PROP_POS_MSEC, video_time_ms)
        success, frame = capture.read()
        if not success or frame is None:
            raise ValueError(f"Could not decode a frame from {path}")
        encoded, buffer = cv2.imencode(".jpg", frame)
        if not encoded:
            raise ValueError(f"Could not encode a frame from {path}")
        return buffer.tobytes(), "VIDEO_FRAME", "image/jpeg"
    finally:
        capture.release()


def _probe_file_uploads(
    client: httpx.Client,
    *,
    image_path: Path | None,
    video_path: Path | None,
    video_time_ms: int,
) -> list[dict[str, Any]]:
    username = os.getenv("SEED_OPERATOR_USERNAME", "operator")
    password = os.getenv("SEED_OPERATOR_PASSWORD")
    if not password:
        return [_hold("file_upload_inference", "SEED_OPERATOR_PASSWORD is not configured")]
    if image_path is None or video_path is None:
        return [
            _hold(
                "file_upload_inference",
                "Both --image and --video acceptance media are required",
            )
        ]

    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if login.status_code != 200:
        return [_fail("file_upload_inference", f"Operator login returned {login.status_code}")]
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    lanes = client.get("/api/v1/lanes/active", headers=headers)
    if lanes.status_code != 200:
        return [_fail("file_upload_inference", f"Lane lookup returned {lanes.status_code}")]
    lane = next((row for row in lanes.json() if row.get("direction") == "IN"), None)
    if lane is None:
        return [_fail("file_upload_inference", "No active IN lane is available")]

    checks = []
    for path in (image_path, video_path):
        try:
            body, input_kind, media_type = _media_bytes(path, video_time_ms=video_time_ms)
        except (OSError, ValueError) as exc:
            checks.append(_hold(f"{path.name}_inference", str(exc)))
            continue
        form_data = {
            "lane_id": lane["id"],
            "mode": "preview",
            "persist": "false",
            "input_kind": input_kind,
        }
        if input_kind == "VIDEO_FRAME":
            form_data["video_time_ms"] = str(video_time_ms)
        response = client.post(
            "/api/v1/alpr/detections",
            headers=headers,
            data=form_data,
            files={"image": (path.name, body, media_type)},
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"body": response.text[-2000:]}
        name = f"{input_kind.lower()}_real_inference"
        if response.status_code != 200:
            checks.append(
                _fail(name, f"Inference returned HTTP {response.status_code}", response=payload)
            )
            continue
        if payload.get("provider") in {None, "mock", "test", "unknown"}:
            checks.append(_fail(name, "Inference did not use the real provider", response=payload))
            continue
        checks.append(
            _pass(
                name,
                media=str(path.resolve()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                provider=payload.get("provider"),
                model_version=payload.get("model_version"),
                input_kind=input_kind,
                normalized_plate=payload.get("normalized_plate"),
                requires_confirmation=payload.get("requires_confirmation"),
            )
        )
    return checks


def run_system_gate(
    *,
    backend_url: str,
    frontend_url: str,
    image_path: Path | None,
    video_path: Path | None,
    video_time_ms: int,
) -> tuple[GateStatus, dict[str, Any]]:
    checks = [
        _run_command("model_bundle_checksums", [sys.executable, "scripts/verify_model_bundle.py"]),
        _run_command(
            "cash_workflow_tests",
            [sys.executable, "-m", "pytest", "tests/integration/test_e2e_cash_workflow.py", "-q"],
        ),
    ]

    with httpx.Client(base_url=backend_url.rstrip("/"), timeout=120) as client:
        runtime = _runtime_health(client)
        checks.append(runtime)
        if runtime["status"] == GateStatus.PASS:
            checks.extend(
                _probe_file_uploads(
                    client,
                    image_path=image_path,
                    video_path=video_path,
                    video_time_ms=video_time_ms,
                )
            )
    checks.append(_frontend_health(frontend_url))

    status = aggregate_status(checks)
    report = {
        "gate": "SYSTEM_FUNCTIONAL",
        "operating_mode": "FILE_UPLOAD",
        "live_camera_rtsp": "NOT_INTEGRATED",
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": _git_commit(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "backend_url": backend_url,
            "frontend_url": frontend_url,
        },
        "status": status,
        "checks": checks,
    }
    return status, report


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="VisionPark real-system functional gate")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--video-time-ms", type=int, default=0)
    parser.add_argument(
        "--report",
        type=Path,
        default=BACKEND_DIR / "var" / "reports" / "system-functional-gate.json",
    )
    args = parser.parse_args()

    status, report = run_system_gate(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        image_path=args.image,
        video_path=args.video,
        video_time_ms=args.video_time_ms,
    )
    _write_report(args.report, report)
    print(json.dumps({"status": status, "report": str(args.report)}, ensure_ascii=False))
    return ExitCode[status.name]


if __name__ == "__main__":
    raise SystemExit(main())
