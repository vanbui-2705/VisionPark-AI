"""Unit tests for Fire and Smoke Detector Runtime with 5-layer filtering (SPEC-AI-03)."""

import hashlib
import json
import sys
from types import SimpleNamespace

import numpy as np

from app.alpr.fire_provider import FireSmokeDetectorRuntime


def write_fire_manifest(tmp_path) -> str:
    weights_path = tmp_path / "fire.onnx"
    weights_path.write_bytes(b"dummy_fire_weights")
    manifest = {
        "model_name": "visionpark-fire-smoke",
        "model_version": "ultralytics-onnx-fire-smoke-v1",
        "detector": {
            "weights_path": "fire.onnx",
            "sha256": hashlib.sha256(b"dummy_fire_weights").hexdigest(),
            "classes": {"0": "fire", "1": "smoke"},
            "confidence_thresholds": {"fire": 0.45, "smoke": 0.40},
            "imgsz": 640,
        },
        "rules": {
            "temporal_debounce_frames": 5,
            "temporal_window_seconds": 3.0,
            "smoke_persistence_seconds": 2.0,
        },
    }
    manifest_path = tmp_path / "fire-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return str(manifest_path)


class FakeBoxes:
    def __init__(self, classes, confidences, coordinates):
        self.cls = classes
        self.conf = confidences
        self.xyxy = coordinates

    def __len__(self):
        return len(self.cls)


class FakePrediction:
    def __init__(self, boxes):
        self.boxes = boxes


def test_fire_runtime_temporal_debounce(tmp_path, monkeypatch):
    """Test Layer 2: requires at least 5 frames within window to trigger alarm."""

    class FakeYOLO:
        names = {0: "fire", 1: "smoke"}

        def __init__(self, weights_path, *args, **kwargs):
            pass

        def predict(self, **kwargs):
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[0]],
                        confidences=[[0.75]],
                        coordinates=[[100, 100, 200, 200]],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = FireSmokeDetectorRuntime(write_fire_manifest(tmp_path))

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cam_id = "cam-b1-zone-01"

    # Frame 1 to 4: should NOT emit an event yet
    for i in range(4):
        events = runtime.process_frame(frame, cam_id, timestamp=100.0 + i * 0.2)
        assert len(events) == 0

    # Frame 5 (>= 5 frames in 3s window): MUST emit event
    events = runtime.process_frame(frame, cam_id, timestamp=100.8)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "FIRE"
    assert ev.confirmed_frame_count == 5
    assert ev.status in ("VERIFYING", "CONFIRMED")


def test_fire_runtime_exclusion_mask(tmp_path, monkeypatch):
    """Test Layer 3: Static exclusion mask suppresses fixed lamp/reflection."""

    class FakeYOLO:
        names = {0: "fire", 1: "smoke"}

        def __init__(self, weights_path, *args, **kwargs):
            pass

        def predict(self, **kwargs):
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[0]],
                        confidences=[[0.85]],
                        coordinates=[[50, 50, 80, 80]],  # Light bulb area
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = FireSmokeDetectorRuntime(write_fire_manifest(tmp_path))

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cam_id = "cam-b1-ceiling"

    # Define exclusion mask matching the static light
    settings = {"exclusion_masks": [(40, 40, 90, 90)]}

    # Feed 10 frames: should be ignored because it is inside exclusion zone
    for i in range(10):
        events = runtime.process_frame(frame, cam_id, settings=settings, timestamp=200.0 + i * 0.2)
        assert len(events) == 0


def test_smoke_persistence_filter(tmp_path, monkeypatch):
    """Test Layer 4: Smoke that shrinks/dissipates within 1 second is suppressed."""
    shrink_step = 0

    class FakeYOLO:
        names = {0: "fire", 1: "smoke"}

        def __init__(self, weights_path, *args, **kwargs):
            pass

        def predict(self, **kwargs):
            nonlocal shrink_step
            # Smoke shrinks rapidly (e.g. exhaust puff)
            area_offset = shrink_step * 15
            shrink_step += 1
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[1]],
                        confidences=[[0.60]],
                        coordinates=[
                            [
                                100 + area_offset,
                                100 + area_offset,
                                250 - area_offset,
                                250 - area_offset,
                            ]
                        ],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = FireSmokeDetectorRuntime(write_fire_manifest(tmp_path), smoke_persistence_seconds=3.0)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cam_id = "cam-gate-exhaust"

    # Rapid puff over 5 frames in 0.8s
    events = []
    for i in range(5):
        events = runtime.process_frame(frame, cam_id, timestamp=300.0 + i * 0.2)

    # Smoke shrank and didn't persist past 3s -> suppressed
    assert len(events) == 0
