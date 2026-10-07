"""Real-provider persistence checks on the isolated restored environment only."""

import hashlib
import json
import subprocess
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
from data_backup import inventory
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DB = "visionpark-restore-e2e-db"
BACKEND = "visionpark-restore-e2e-backend"
COMPOSE = ["docker", "compose", "-f", "deployment/compose.persistence-test.yml"]


def compose(*args):
    subprocess.run([*COMPOSE, *args], cwd=ROOT, check=True)


def wait_ready(api):
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        try:
            response = api.get("/health/ready")
            if response.status_code == 200:
                assert response.json()["alpr"]["provider"] == "real"
                return response.json()
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError("Isolated backend did not become ready")


def main():
    report = {
        "environment": "isolated restored DB and volumes",
        "limitation": (
            "Blank images exercise real inference and no-plate handling; "
            "this is not a real-vehicle accuracy benchmark."
        ),
        "checks": {},
    }
    with httpx.Client(base_url="http://127.0.0.1:8003", timeout=180) as api:
        report["health"] = wait_ready(api)
        login = api.post(
            "/api/v1/auth/login",
            json={"username": "completion-admin", "password": "completion-test-password"},
        )
        login.raise_for_status()
        api.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        lanes = api.get("/api/v1/lanes/active").json()
        lane = next(row for row in lanes if row["direction"] == "IN")
        captures = []
        image_hashes = {}
        for kind, fmt in [("IMAGE_UPLOAD", "PNG"), ("VIDEO_FRAME", "JPEG")]:
            image = BytesIO()
            Image.new("RGB", (640, 480), "gray").save(image, fmt)
            data = {"lane_id": lane["id"], "input_kind": kind, "mode": "preview"}
            if kind == "VIDEO_FRAME":
                data["video_time_ms"] = "333"
            media_type = "image/png" if fmt == "PNG" else "image/jpeg"
            files = {"image": ("capture." + fmt.lower(), image.getvalue(), media_type)}
            preview = api.post("/api/v1/alpr/detections", data=data, files=files)
            preview.raise_for_status()
            assert preview.json()["provider"] == "ultralytics-paddleocr"
            assert preview.json()["normalized_plate"] is None
            assert preview.json()["detection_id"] is None
            capture = str(uuid4())
            data.update(mode="final", capture_id=capture)
            for _ in range(2):
                final = api.post("/api/v1/alpr/detections", data=data, files=files)
                final.raise_for_status()
                assert final.json()["detection_id"] == capture
                assert final.json()["input_kind"] == kind
            detail = api.get("/api/v1/alpr/detections/" + capture).json()
            stored_image = api.get("/api/v1/alpr/media/" + detail["image_key"])
            stored_image.raise_for_status()
            assert stored_image.content == image.getvalue()
            assert stored_image.headers["content-type"].startswith(media_type)
            image_hashes[capture] = hashlib.sha256(stored_image.content).hexdigest()
            captures.append(capture)
        report["checks"]["image_video_real_no_plate_final_retry_media"] = "pass"
        capture = captures[0]
        headers = {"Idempotency-Key": str(uuid4())}
        payload = {
            "confirmed_plate": "99Z12345",
            "check_in": True,
            "source": "OPERATOR_CORRECTED",
            "override_reason": "Isolated workflow verification: blank image has no plate.",
        }
        confirmed = api.post(
            "/api/v1/alpr/detections/" + capture + "/confirm", json=payload, headers=headers
        )
        confirmed.raise_for_status()
        retried = api.post(
            "/api/v1/alpr/detections/" + capture + "/confirm", json=payload, headers=headers
        )
        retried.raise_for_status()
        assert confirmed.json()["transaction"]["id"] == retried.json()["transaction"]["id"]
        assert (
            api.get(
                "/api/v1/parking/transactions", params={"paginated": True, "q": "99Z12345"}
            ).json()["total"]
            == 1
        )
        report["checks"]["correction_transaction_idempotency"] = "pass"
        pref = {"theme": "dark", "language": "en"}
        api.put("/api/v1/auth/preferences", json=pref).raise_for_status()
        correlation = str(uuid4())
        error = {
            "code": "WORKFLOW_VERIFY",
            "status": 503,
            "source": "acceptance",
            "correlation_id": correlation,
        }
        e1 = api.post("/api/v1/errors", json=error)
        e2 = api.post("/api/v1/errors", json=error)
        assert e1.json()["id"] == e2.json()["id"]
        notification = api.get("/api/v1/notifications").json()["items"][0]
        api.post("/api/v1/notifications/" + notification["id"] + "/read").raise_for_status()
        baseline = inventory(DB, BACKEND)
        assert not {"visionpark_postgres_data", "visionpark_media_data"} & set(baseline["volumes"])
        for operation in ["restart", "down_up", "force_recreate"]:
            print("Persistence check: " + operation, flush=True)
            if operation == "restart":
                compose("restart")
            elif operation == "down_up":
                compose("down")
                compose("up", "-d")
            else:
                compose("up", "-d", "--force-recreate")
            wait_ready(api)
            after = inventory(DB, BACKEND)
            assert after == baseline, (operation, baseline, after)
            assert api.get("/api/v1/auth/preferences").json() == pref
            assert any(
                n["id"] == notification["id"] and n["read"]
                for n in api.get("/api/v1/notifications").json()["items"]
            )
            for capture in captures:
                detail = api.get("/api/v1/alpr/detections/" + capture).json()
                stored = api.get("/api/v1/alpr/media/" + detail["image_key"])
                assert hashlib.sha256(stored.content).hexdigest() == image_hashes[capture]
            report["checks"][operation + "_rows_and_media_unchanged"] = "pass"
        report["inventory"] = baseline
        report["capture_ids"] = captures
    target = ROOT / "docs/phase-2-evidence/completion-persistence.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
