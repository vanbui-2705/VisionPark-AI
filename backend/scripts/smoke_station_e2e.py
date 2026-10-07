"""Exercise the local Compose UI with a synthetic video and disposable QA records.

Run from backend after installing .[e2e] and Playwright Chromium. Configuration
comes from the ignored root .env. This script never prints credentials or tokens.
"""

import json
import os
import platform
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

import app.database.models  # noqa: F401
from app.modules.alpr.models import Detection
from app.modules.audit_logs.models import AuditLog
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane


def main():
    root = Path(__file__).resolve().parents[2]
    config = dotenv_values(root / ".env")
    if config.get("ENVIRONMENT", "development") != "development":
        raise RuntimeError("This smoke script requires the local development environment.")
    base = f"http://127.0.0.1:{config.get('FRONTEND_PORT', '5173')}"
    evidence = root / "docs" / "phase-2-evidence"
    evidence.mkdir(exist_ok=True)
    video = root / "backend" / "var" / "fixtures" / "station-smoke.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=640x480:r=10",
            "-t",
            "3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    url = URL.create(
        "postgresql+psycopg",
        username=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
        host="127.0.0.1",
        port=int(config["POSTGRES_PORT"]),
        database=config["POSTGRES_DB"],
    )
    engine = create_engine(url)
    lane_id = None
    report = {"input": "synthetic gray MP4", "provider": "backend mock", "checks": {}}
    with httpx.Client(base_url=base, follow_redirects=True, timeout=20) as api:
        health = api.get("/health/ready")
        health.raise_for_status()
        if health.json()["alpr"]["provider"] != "mock":
            raise RuntimeError(
                "This browser smoke requires backend mock ALPR. "
                "Use smoke_real_alpr.py for the real-provider sanity check."
            )
        admin = api.post(
            "/api/v1/auth/login",
            json={
                "username": config["SEED_ADMIN_USERNAME"],
                "password": config["SEED_ADMIN_PASSWORD"],
            },
        )
        admin.raise_for_status()
        admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
        assert api.get("/api/v1/users", headers=admin_headers).status_code == 200
        roles = api.get("/api/v1/roles", headers=admin_headers)
        assert roles.status_code == 200
        assert {row["name"] for row in roles.json()} == {
            "ADMIN",
            "OPERATOR",
            "ACCOUNTANT",
            "TECHNICIAN",
        }
        report["checks"]["admin_users_roles_endpoints"] = "pass"
        lane = api.post(
            "/api/v1/lanes/",
            headers=admin_headers,
            json={
                "name": f"qa-integration-{uuid4().hex[:8]}",
                "direction": "IN",
                "video_source": "station-smoke.mp4",
                "is_active": True,
            },
        )
        lane.raise_for_status()
        lane_id = UUID(lane.json()["id"])
        try:
            with sync_playwright() as playwright:
                # Playwright's Windows Chromium omits H.264; use installed Edge for MP4.
                channel = os.getenv("E2E_BROWSER_CHANNEL") or (
                    "msedge" if platform.system() == "Windows" else "chromium"
                )
                browser = playwright.chromium.launch(headless=True, channel=channel)
                report["browser_channel"] = channel
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base + "/login")
                page.get_by_label("Tên đăng nhập", exact=True).fill(
                    config["SEED_OPERATOR_USERNAME"]
                )
                page.get_by_label("Mật khẩu", exact=True).fill(config["SEED_OPERATOR_PASSWORD"])
                page.get_by_role("button", name="Đăng nhập", exact=True).click()
                expect(page.get_by_role("heading", name="Trạm quét biển số")).to_be_visible()
                token = page.evaluate("localStorage.getItem('visionpark.access_token')")
                operator_headers = {"Authorization": f"Bearer {token}"}
                assert api.get("/api/v1/users", headers=operator_headers).status_code == 403
                report["checks"]["operator_cannot_manage_users"] = "pass"
                page.get_by_label("Lane", exact=True).select_option(str(lane_id))
                page.get_by_label("Video MP4", exact=True).set_input_files(str(video))
                page.wait_for_function("document.querySelector('video')?.readyState >= 2")
                for _ in range(2):
                    with page.expect_response(
                        lambda r: r.request.method == "POST" and r.url.endswith("/alpr/detections")
                    ) as captured:
                        page.get_by_role("button", name="Capture Frame", exact=True).click()
                    assert captured.value.status == 200
                    expect(
                        page.get_by_role("button", name="Capture Frame", exact=True)
                    ).to_be_enabled()
                expect(page.get_by_text("Kết quả ổn định.", exact=True)).to_be_visible()
                expect(page.get_by_text("MOCK ALPR", exact=True)).to_be_visible()
                with Session(engine) as db:
                    assert not db.scalar(select(Detection).where(Detection.lane_id == lane_id))
                page.screenshot(path=str(evidence / "mock-preview.png"), full_page=True)
                report["checks"]["preview_without_persistence"] = "pass"
                plate = "93Q" + str(int(uuid4().hex[:8], 16) % 100000).zfill(5)

                def correct_plate():
                    page.get_by_role("button", name="✎ Sai / Không có biển", exact=True).click()
                    expect(
                        page.get_by_role("button", name="Capture Frame", exact=True)
                    ).to_be_disabled()
                    page.get_by_label("Biển số chính xác", exact=True).fill(plate)
                    with page.expect_response(lambda r: r.url.endswith("/confirm")) as confirmed:
                        page.get_by_role("button", name="Xác nhận sửa", exact=True).click()
                    return confirmed.value

                confirmed = correct_plate()
                assert confirmed.status == 200, confirmed.text()
                transaction = confirmed.json()["transaction"]
                expect(page.get_by_text("Check-in thành công.", exact=True)).to_be_visible()
                page.screenshot(path=str(evidence / "mock-corrected-checkin.png"), full_page=True)
                report["checks"]["ui_confirm_persisted_parked"] = "pass"
                replay = api.post(
                    confirmed.url,
                    headers={
                        **operator_headers,
                        "Idempotency-Key": confirmed.request.headers["idempotency-key"],
                    },
                    json={"confirmed_plate": plate, "check_in": True},
                )
                assert replay.status_code == 200
                assert replay.json()["transaction"]["id"] == transaction["id"]
                report["checks"]["idempotent_retry"] = "pass"
                page.get_by_role("button", name="Xe tiếp theo", exact=True).click()
                with page.expect_response(
                    lambda r: r.request.method == "POST" and r.url.endswith("/alpr/detections")
                ):
                    page.get_by_role("button", name="Capture Frame", exact=True).click()
                expect(page.get_by_role("button", name="Capture Frame", exact=True)).to_be_enabled()
                duplicate = correct_plate()
                assert duplicate.status == 409
                assert duplicate.json()["code"] == "PLATE_ALREADY_PARKED"
                expect(page.get_by_text("PLATE_ALREADY_PARKED (409)", exact=True)).to_be_visible()
                page.screenshot(path=str(evidence / "mock-duplicate.png"), full_page=True)
                report["checks"]["duplicate_rejected"] = "pass"
                page.get_by_role("button", name="Hủy sửa", exact=True).click()
                page.route(
                    "**/api/v1/alpr/detections",
                    lambda route: route.fulfill(
                        status=503,
                        json={
                            "code": "DEPENDENCY_UNAVAILABLE",
                            "message": "Injected provider failure for UI smoke",
                        },
                    ),
                )
                page.get_by_role("button", name="Capture Frame", exact=True).click()
                expect(page.get_by_text("DEPENDENCY_UNAVAILABLE (503)", exact=True)).to_be_visible()
                page.get_by_label("Biển số nhập tay", exact=True).fill("94Q" + plate[3:])
                with page.expect_response(lambda r: r.url.endswith("/parking/check-in")) as manual:
                    page.get_by_role("button", name="Tạo check-in", exact=True).click()
                assert manual.value.status == 201
                expect(page.get_by_text("Check-in thành công.", exact=True)).to_be_visible()
                page.screenshot(path=str(evidence / "manual-provider-failure.png"), full_page=True)
                report["checks"]["manual_fallback_after_injected_503"] = "pass"
                with Session(engine) as db:
                    transactions = db.scalars(
                        select(ParkingTransaction).where(ParkingTransaction.lane_id == lane_id)
                    ).all()
                    assert len(transactions) == 2
                    assert {item.source for item in transactions} == {
                        "OPERATOR_CORRECTED",
                        "MANUAL_ENTRY",
                    }
                    assert all(item.status == "PARKED" for item in transactions)
                page.goto(base + f"/detections/{transaction['detection_id']}")
                expect(page.get_by_text(plate, exact=True).first).to_be_visible()
                page.get_by_role("button", name="Media", exact=True).click()
                page.wait_for_function("document.querySelector('img')?.naturalWidth > 0")
                report["checks"]["detection_detail_media"] = "pass"
                assert not page_errors, page_errors
                report["checks"]["browser_errors"] = 0
                browser.close()
        finally:
            # Only records owned by this uniquely named QA lane are removed.
            with Session(engine) as db:
                qa_lane = db.get(Lane, lane_id)
                assert qa_lane and qa_lane.name.startswith("qa-integration-")
                detections = db.scalars(select(Detection).where(Detection.lane_id == lane_id)).all()
                transactions = db.scalars(
                    select(ParkingTransaction).where(ParkingTransaction.lane_id == lane_id)
                ).all()
                owned_ids = [str(lane_id)] + [str(row.id) for row in detections + transactions]
                image_keys = [row.image_key for row in detections]
                db.execute(delete(AuditLog).where(AuditLog.entity_id.in_(owned_ids)))
                db.execute(delete(ParkingTransaction).where(ParkingTransaction.lane_id == lane_id))
                db.execute(delete(Detection).where(Detection.lane_id == lane_id))
                db.execute(delete(Lane).where(Lane.id == lane_id))
                db.commit()
            cleanup = (
                "from pathlib import Path\n"
                f"folder=Path('/app/var/media') / {str(lane_id)!r}\n"
                f"for key in {image_keys!r}:\n"
                " path=folder/key\n"
                " assert path.parent == folder\n"
                " path.unlink(missing_ok=True)\n"
                "if folder.exists(): folder.rmdir()\n"
            )
            subprocess.run(
                ["docker", "exec", "-i", "visionpark-backend-1", "python", "-"],
                input=cleanup,
                text=True,
                check=True,
            )
            engine.dispose()
            report["qa_records_removed"] = True
    (evidence / "browser-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
