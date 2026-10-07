"""Exercise actual image/video Station UI against the isolated acceptance server."""

import json
import re
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright
from smoke_completion import wait_ready

ROOT = Path(__file__).resolve().parents[2]


def main():
    with httpx.Client(base_url="http://localhost:8003", timeout=180) as api:
        wait_ready(api)
    video = next(Path("C:/Users/bui van/Downloads").glob("*dxJC4GXu4mc*.mp4"))
    report = {"environment": "isolated restored environment", "checks": {}, "captures": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(120000)
        page.goto("http://localhost:5175/login")
        page.locator("input[name=username]").fill("completion-admin")
        page.locator("input[name=password]").fill("completion-test-password")
        page.locator("button[type=submit]").click()
        page.wait_for_url(re.compile(r".*/(dashboard|station|admin).*"))
        page.goto("http://localhost:5175/station")
        page.locator("#lane-select option").nth(1).wait_for(state="attached")
        lane = page.locator("#lane-select option").nth(1).get_attribute("value")
        page.locator("#lane-select").select_option(lane)
        page.locator("select").first.select_option("image")
        page.locator("input[type=file]").set_input_files(
            str(ROOT / "backend/var/completion-video/frame-45.jpg")
        )
        with page.expect_response(
            lambda r: "/alpr/detections" in r.url and r.request.method == "POST"
        ) as pending:
            page.get_by_role("button", name=re.compile("Nhận diện ảnh|Recognize image")).click()
        result = pending.value.json()
        assert result["normalized_plate"] == "29A90101", result
        assert result["input_kind"] == "IMAGE_UPLOAD"
        with page.expect_response(
            lambda r: r.url.endswith("/confirm") and r.request.method == "POST"
        ) as confirmed:
            page.get_by_role("button", name=re.compile("✓")).click()
        if confirmed.value.status == 409:
            assert confirmed.value.json()["code"] == "PLATE_ALREADY_PARKED"
            token = page.evaluate('localStorage.getItem("visionpark.access_token")')
            with httpx.Client(
                base_url="http://localhost:8003", headers={"Authorization": "Bearer " + token}
            ) as api:
                transaction = api.get(
                    "/api/v1/parking/transactions", params={"q": "29A90101"}
                ).json()[0]
            report["checks"]["repeat_image_checkin_duplicate_rejected"] = "pass"
        else:
            assert confirmed.value.status == 200, confirmed.value.text()
            transaction = confirmed.value.json()["transaction"]
        report["captures"].append({"kind": "IMAGE_UPLOAD", "transaction": transaction})
        page.screenshot(
            path=str(ROOT / "docs/phase-2-evidence/completion-image-station.png"), full_page=True
        )
        report["checks"]["real_image_recognize_confirm_history"] = "pass"
        if confirmed.value.status == 200:
            page.get_by_role("button", name=re.compile("Xe tiếp theo|Next vehicle")).click()
        else:
            page.locator("select").first.select_option("video")
            page.locator("select").first.select_option("image")
            page.locator("input[type=file]").set_input_files(
                str(ROOT / "backend/var/completion-video/frame-45.jpg")
            )
        with page.expect_response(
            lambda r: "/alpr/detections" in r.url and r.request.method == "POST"
        ):
            page.get_by_role("button", name=re.compile("Nhận diện ảnh|Recognize image")).click()
            page.locator("select").first.select_option("video")
        page.get_by_text("Status: IDLE", exact=False).wait_for()
        report["checks"]["switch_mode_ignores_pending_image_result"] = "pass"
        page.locator("input[type=file]").set_input_files(str(video))
        page.wait_for_function('document.querySelector("video")?.readyState >= 2')
        page.evaluate('document.querySelector("video").currentTime = 90')
        page.wait_for_function(
            'Math.abs(document.querySelector("video").currentTime - 90) < 0.05 '
            '&& !document.querySelector("video").seeking'
        )
        with page.expect_response(
            lambda r: "/alpr/detections" in r.url and r.request.method == "POST"
        ) as pending:
            page.get_by_role("button", name="Capture Frame", exact=True).click()
        result = pending.value.json()
        assert result["normalized_plate"] == "30V4495", result
        assert result["input_kind"] == "VIDEO_FRAME"
        assert abs(result["video_time_ms"] - 90000) < 100
        with page.expect_response(
            lambda r: r.url.endswith("/confirm") and r.request.method == "POST"
        ) as confirmed:
            page.get_by_role("button", name=re.compile("✓")).click()
        assert confirmed.value.status == 200, confirmed.value.text()
        report["captures"].append(
            {"kind": "VIDEO_FRAME", "transaction": confirmed.value.json()["transaction"]}
        )
        page.screenshot(
            path=str(ROOT / "docs/phase-2-evidence/completion-video-station.png"), full_page=True
        )
        report["checks"]["real_mp4_frame_recognize_confirm_history"] = "pass"
        browser.close()
    (ROOT / "docs/phase-2-evidence/completion-browser.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    main()
