"""Unit tests for Dual Detection (Vehicle + Plate) and Association (SPEC-AI-01)."""

import hashlib
import json
import sys
from types import SimpleNamespace

import cv2
import numpy as np

from app.alpr.pt_provider import UltralyticsPaddleALPRRuntime
from app.alpr.schema import VehicleType


def write_dual_manifest(tmp_path) -> str:
    weights_path = tmp_path / "plate.onnx"
    weights_path.write_bytes(b"dummy_weights")
    manifest = {
        "model_name": "visionpark-alpr-dual",
        "model_version": "ultralytics-onnx-plate-vehicle-v1",
        "detector": {
            "weights_path": "plate.onnx",
            "sha256": hashlib.sha256(b"dummy_weights").hexdigest(),
            "classes": {
                "0": "car",
                "1": "motorcycle",
                "2": "plate",
                "3": "bicycle",
            },
            "plate_class": "plate",
            "imgsz": 640,
            "confidence_thresholds": {
                "plate": 0.30,
                "car": 0.45,
                "motorcycle": 0.40,
                "bicycle": 0.35,
            },
        },
    }
    manifest_path = tmp_path / "alpr-manifest.json"
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


def test_dual_detection_associates_plate_inside_car(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {0: "car", 1: "motorcycle", 2: "plate", 3: "bicycle"}

        def __init__(self, weights_path):
            pass

        def predict(self, **kwargs):
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[0], [2]],
                        confidences=[[0.92], [0.88]],
                        coordinates=[
                            [50, 50, 400, 300],  # Car box
                            [120, 200, 240, 260],  # Plate box inside the car
                        ],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_dual_manifest(tmp_path), ocr_enabled=False)

    img = np.full((400, 500, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)

    result = runtime.detect_and_read(buf.tobytes())

    assert result.bbox is not None
    assert result.bbox.model_dump() == {"x1": 120, "y1": 200, "x2": 240, "y2": 260}
    assert result.vehicle_type == VehicleType.CAR.value
    assert result.vehicle_confidence == 0.92
    assert result.bbox_vehicle is not None
    assert result.bbox_vehicle.model_dump() == {"x1": 50, "y1": 50, "x2": 400, "y2": 300}


def test_dual_detection_handles_bicycle_without_plate(tmp_path, monkeypatch):
    """Test BR-20: Bicycles do not require license plates."""

    class FakeYOLO:
        names = {0: "car", 1: "motorcycle", 2: "plate", 3: "bicycle"}

        def __init__(self, weights_path):
            pass

        def predict(self, **kwargs):
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[3]],
                        confidences=[[0.85]],
                        coordinates=[[10, 10, 150, 200]],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_dual_manifest(tmp_path), ocr_enabled=False)

    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)

    result = runtime.detect_and_read(buf.tobytes())

    assert result.vehicle_type == VehicleType.BICYCLE.value
    assert result.plate_number is None
    assert result.bbox is None
    assert result.vehicle_confidence == 0.85
    assert result.bbox_vehicle is not None
    assert result.bbox_vehicle.model_dump() == {"x1": 10, "y1": 10, "x2": 150, "y2": 200}


def test_dual_detection_with_dynamic_settings(tmp_path, monkeypatch):
    """Test dynamic override from Building Settings."""

    class FakeYOLO:
        names = {0: "car", 1: "motorcycle", 2: "plate", 3: "bicycle"}

        def __init__(self, weights_path):
            pass

        def predict(self, **kwargs):
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[0], [2]],
                        confidences=[[0.60], [0.55]],
                        coordinates=[[10, 10, 200, 200], [50, 80, 120, 110]],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_dual_manifest(tmp_path), ocr_enabled=False)

    img = np.full((300, 300, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)

    # Pass dynamic settings with building_id
    settings = {
        "building_id": "bldg-hanoi-01",
        "car_confidence": 0.50,
        "plate_confidence": 0.50,
        "confirmation_threshold": 0.70,
    }
    result = runtime.detect_and_read(buf.tobytes(), settings=settings)

    assert result.building_id == "bldg-hanoi-01"
    assert result.vehicle_type == VehicleType.CAR.value
    assert result.vehicle_confidence == 0.60
