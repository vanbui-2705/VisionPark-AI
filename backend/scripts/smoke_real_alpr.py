"""Verify real Docker inference without storing vehicle records or claiming accuracy."""

import json
import subprocess
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import dotenv_values
from PIL import Image


def main():
    root = Path(__file__).resolve().parents[2]
    config = dotenv_values(root / ".env")
    base = f"http://127.0.0.1:{config.get('FRONTEND_PORT', '5173')}"
    report = {"input": "synthetic blank image and rendered text crop", "checks": {}}
    with httpx.Client(base_url=base, follow_redirects=True, timeout=120) as api:
        ready = api.get("/health/ready")
        ready.raise_for_status()
        health = ready.json()
        assert health["alpr"]["provider"] == "real", health
        assert health["alpr"]["ocr_enabled"] is True, health
        report["health"] = health
        report["checks"]["real_detector_and_ocr_ready"] = "pass"
        login = api.post(
            "/api/v1/auth/login",
            json={
                "username": config["SEED_OPERATOR_USERNAME"],
                "password": config["SEED_OPERATOR_PASSWORD"],
            },
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        lanes = api.get("/api/v1/lanes/active", headers=headers)
        lanes.raise_for_status()
        lane = next(row for row in lanes.json() if row["direction"] == "IN")
        image = BytesIO()
        Image.new("RGB", (640, 480), "gray").save(image, "JPEG")
        response = api.post(
            "/api/v1/alpr/detections",
            headers=headers,
            data={"lane_id": lane["id"], "mode": "preview", "persist": "false"},
            files={"image": ("blank.jpg", image.getvalue(), "image/jpeg")},
        )
        response.raise_for_status()
        result = response.json()
        assert result["provider"] == "ultralytics-paddleocr", result
        assert result["normalized_plate"] is None, result
        assert result["detection_id"] is None, result
        report["blank_frame"] = result
        report["checks"]["blank_frame_does_not_return_mock_plate"] = "pass"
    # Exercise the actual recognition model separately because the blank frame
    # intentionally contains no detector crop. This is not a real-vehicle benchmark.
    code = """
import json
import cv2
import numpy as np
from app.main import app
runtime = app.state.alpr_runtime
assert runtime.is_ready()[0]
crop = np.full((96, 400, 3), 255, dtype=np.uint8)
cv2.putText(crop, '30F12345', (12, 68), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3, cv2.LINE_AA)
result = runtime._ocr.recognize(crop)
assert result.normalized_text, 'OCR returned no text on the rendered sanity crop'
body = {'raw_text': result.raw_text, 'normalized_text': result.normalized_text,
        'confidence': result.confidence}
print('OCR_SMOKE_JSON=' + json.dumps(body))
"""
    output = subprocess.check_output(
        ["docker", "compose", "exec", "-T", "backend", "python", "-"],
        input=code,
        text=True,
        cwd=root,
        timeout=180,
    )
    line = next(line for line in output.splitlines() if line.startswith("OCR_SMOKE_JSON="))
    report["rendered_text_ocr"] = json.loads(line.split("=", 1)[1])
    report["checks"]["actual_ocr_inference_on_rendered_crop"] = "pass"
    report["limitation"] = "Synthetic sanity checks; no real-vehicle accuracy/latency claim."
    evidence = root / "docs/phase-2-evidence/real-provider-smoke.json"
    evidence.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
