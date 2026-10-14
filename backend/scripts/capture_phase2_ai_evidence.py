"""Capture traceable real-provider browser evidence for the remaining Phase 2 AI gates."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "phase-2-evidence"
API_URL = "http://127.0.0.1:8003"
WEB_URL = "http://127.0.0.1:5175"


def audit_for(api: httpx.Client, resource_id: str) -> list[dict]:
    response = api.get(
        "/api/v1/audit-logs/",
        params={"resource_id": resource_id, "limit": 100},
    )
    response.raise_for_status()
    return response.json()


def transaction_ids(api: httpx.Client) -> list[str]:
    response = api.get("/api/v1/parking/transactions", params={"limit": 100})
    response.raise_for_status()
    payload = response.json()
    rows = payload["data"] if isinstance(payload, dict) else payload
    return sorted(row["id"] for row in rows)


def main() -> None:
    report: dict = {
        "environment": "isolated Phase 2 real-provider evidence environment",
        "model_version": None,
        "checks": {},
        "scenarios": {},
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(120000)
        page.goto(f"{WEB_URL}/login")
        page.locator("input[name=username]").fill("completion-admin")
        page.locator("input[name=password]").fill("completion-test-password")
        page.locator("button[type=submit]").click()
        page.wait_for_url(re.compile(r".*/(dashboard|station|admin).*"))
        page.goto(f"{WEB_URL}/station")
        page.locator("#lane-select option").nth(1).wait_for(state="attached")
        page.locator("#lane-select").select_option(
            page.locator("#lane-select option").nth(1).get_attribute("value")
        )
        page.locator("select").first.select_option("image")

        low_confidence_input = ROOT / "backend/var/completion-video/case-toyota-44.5.jpg"
        page.locator("input[type=file]").set_input_files(str(low_confidence_input))
        with page.expect_response(
            lambda response: "/alpr/detections" in response.url
            and response.request.method == "POST"
        ) as preview_response:
            page.locator("input[type=file]").locator("xpath=following::button[1]").click()
        preview = preview_response.value.json()
        assert preview["requires_confirmation"] is True, preview
        assert preview["normalized_plate"] != "29A90101", preview
        report["model_version"] = preview["model_version"]
        page.get_by_text("Status: NEEDS_CONFIRMATION", exact=False).wait_for()
        page.screenshot(
            path=str(EVIDENCE / "real-low-confidence-before-correction.png"),
            full_page=True,
        )
        page.locator("button").filter(has_text=re.compile("Sai|No plate")).click()
        page.locator("#corrected-plate").fill("29A90101")
        with page.expect_response(
            lambda response: response.url.endswith("/confirm")
            and response.request.method == "POST"
        ) as confirm_response:
            page.locator("#corrected-plate").locator("xpath=following::button[1]").click()
        assert confirm_response.value.status == 200, confirm_response.value.text()
        corrected = confirm_response.value.json()["transaction"]
        assert corrected["original_ai_plate"] == preview["normalized_plate"]
        assert corrected["license_plate"] == "29A90101"
        assert corrected["source"] == "OPERATOR_CORRECTED"
        page.get_by_text("Status: SUCCESS", exact=False).wait_for()
        page.screenshot(path=str(EVIDENCE / "real-low-confidence-corrected.png"), full_page=True)

        token = page.evaluate('localStorage.getItem("visionpark.access_token")')
        with httpx.Client(
            base_url=API_URL,
            headers={"Authorization": "Bearer " + token},
            timeout=60,
        ) as api:
            corrected_audit = audit_for(api, corrected["id"])
            transactions_before_no_plate = transaction_ids(api)
        report["checks"]["real_low_confidence_operator_correction"] = "pass"
        report["scenarios"]["low_confidence"] = {
            "input": str(low_confidence_input.relative_to(ROOT)),
            "preview": preview,
            "transaction": corrected,
            "audit": corrected_audit,
            "screenshots": [
                "real-low-confidence-before-correction.png",
                "real-low-confidence-corrected.png",
            ],
        }

        page.locator("button").filter(has_text=re.compile("Xe tiếp theo|Next vehicle")).click()
        no_plate_input = ROOT / "backend/var/completion-video/case-title-5.jpg"
        page.locator("input[type=file]").set_input_files(str(no_plate_input))
        with page.expect_response(
            lambda response: "/alpr/detections" in response.url
            and response.request.method == "POST"
        ) as no_plate_response:
            page.locator("input[type=file]").locator("xpath=following::button[1]").click()
        no_plate = no_plate_response.value.json()
        assert no_plate["normalized_plate"] is None, no_plate
        assert no_plate["requires_confirmation"] is True, no_plate
        with httpx.Client(
            base_url=API_URL,
            headers={"Authorization": "Bearer " + token},
            timeout=60,
        ) as api:
            transactions_after_no_plate_preview = transaction_ids(api)
        assert transactions_after_no_plate_preview == transactions_before_no_plate
        page.get_by_text("Status: NEEDS_CONFIRMATION", exact=False).wait_for()
        page.screenshot(path=str(EVIDENCE / "real-no-plate-before-manual.png"), full_page=True)
        page.locator("#manual-plate").fill("99N00009")
        with page.expect_response(
            lambda response: response.url.endswith("/parking/check-in")
            and response.request.method == "POST"
        ) as manual_response:
            page.locator("#manual-plate").locator("xpath=following::button[1]").click()
        assert manual_response.value.status == 201, manual_response.value.text()
        manual = manual_response.value.json()["transaction"]
        assert manual["source"] == "MANUAL_ENTRY"
        page.get_by_text("Status: SUCCESS", exact=False).wait_for()
        page.screenshot(path=str(EVIDENCE / "real-no-plate-manual-success.png"), full_page=True)
        with httpx.Client(
            base_url=API_URL,
            headers={"Authorization": "Bearer " + token},
            timeout=60,
        ) as api:
            manual_audit = audit_for(api, manual["id"])
        report["checks"]["real_no_plate_manual_fallback"] = "pass"
        report["scenarios"]["no_plate"] = {
            "input": str(no_plate_input.relative_to(ROOT)),
            "preview": no_plate,
            "preview_transaction_ids_before": transactions_before_no_plate,
            "preview_transaction_ids_after": transactions_after_no_plate_preview,
            "transaction": manual,
            "audit": manual_audit,
            "screenshots": [
                "real-no-plate-before-manual.png",
                "real-no-plate-manual-success.png",
            ],
        }
        browser.close()

    target = EVIDENCE / "real-ai-edge-browser.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    main()
