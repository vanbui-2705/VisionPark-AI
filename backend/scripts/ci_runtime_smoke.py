"""Verify live/database/real-provider readiness without hiding infrastructure failures."""

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def read_json(url: str) -> tuple[int, dict]:
    try:
        response = urlopen(url, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def verify(base_url: str) -> None:
    deadline = time.monotonic() + 180
    while True:
        try:
            status, live = read_json(base_url + "/health/live")
            if status == 200 and live.get("status") == "alive":
                break
        except (URLError, TimeoutError, ConnectionError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError("Backend liveness did not become available")
        time.sleep(1)

    status, ready = read_json(base_url + "/health/ready")
    if ready.get("database", {}).get("status") != "ready":
        raise RuntimeError("Database is not ready")
    alpr = ready.get("alpr", {})
    if alpr.get("provider") != "real":
        raise RuntimeError("Runtime must use the real ALPR provider")
    if status != 200 or ready.get("status") != "ready" or alpr.get("status") != "ready":
        raise RuntimeError("Bundled YOLO and OCR must be ready: " + str(alpr.get("message")))
    if alpr.get("ocr_enabled") is not True:
        raise RuntimeError("OCR must be enabled")
    print("PASS: backend/database/bundled YOLO and OCR ready")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    arguments = parser.parse_args()
    verify(arguments.base_url.rstrip("/"))
