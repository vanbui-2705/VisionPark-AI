"""Run against a local server with demo seed accounts. Never print bearer tokens."""

import json
import os

import cv2
import httpx
import numpy as np

from app.core.config import Settings


def main():
    settings = Settings()
    if settings.seed_operator_password is None:
        raise RuntimeError("Set SEED_OPERATOR_PASSWORD in .env before running the smoke check")
    base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
    with httpx.Client(base_url=base_url, follow_redirects=True, timeout=15) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        assert live.status_code == ready.status_code == 200
        login = client.post(
            "/api/v1/auth/login",
            json={
                "username": settings.seed_operator_username,
                "password": settings.seed_operator_password.get_secret_value(),
            },
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        lanes = client.get("/api/v1/lanes/active", headers=headers)
        assert lanes.status_code == 200 and lanes.json()
        _, image = cv2.imencode(".jpg", np.zeros((24, 40, 3), dtype=np.uint8))
        detection = client.post(
            "/api/v1/alpr/detections",
            headers=headers,
            data={"lane_id": lanes.json()[0]["id"]},
            files={"image": ("smoke.jpg", image.tobytes(), "image/jpeg")},
        )
        assert detection.status_code == 200, detection.text
        forbidden = client.post(
            "/api/v1/lanes/",
            headers=headers,
            json={"name": "SMOKE_FORBIDDEN", "direction": "IN", "video_source": "demo.mp4"},
        )
        assert forbidden.status_code == 403
        unauthenticated = client.get("/api/v1/lanes/")
        assert unauthenticated.status_code == 401
        print(
            json.dumps(
                {
                    "live": live.status_code,
                    "ready": ready.status_code,
                    "login": login.status_code,
                    "lane_list": lanes.status_code,
                    "detection": detection.status_code,
                    "provider": ready.json()["alpr"]["provider"],
                    "model_version": detection.json()["model_version"],
                    "operator_mutation": forbidden.status_code,
                    "unauthenticated": unauthenticated.status_code,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
