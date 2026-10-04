import hashlib
import json
import sys
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.alpr.errors import ALPRInferenceError, ALPRModelMissingError
from app.alpr.ocr_provider import OCRReadResult
from app.alpr.pt_provider import UltralyticsPaddleALPRRuntime


def write_manifest(tmp_path, weights: bytes = b"weights", checksum: str | None = None) -> str:
    weights_path = tmp_path / "best.pt"
    weights_path.write_bytes(weights)
    manifest = {
        "model_version": "test-model-1",
        "detector": {
            "weights_path": "best.pt",
            "sha256": checksum or hashlib.sha256(weights).hexdigest(),
            "plate_class": "plate",
            "imgsz": 640,
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return str(manifest_path)


def image_bytes() -> bytes:
    image = np.full((8, 12, 3), 220, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


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


def test_manifest_and_checksum_are_valid(tmp_path):
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path))

    manifest, weights_path = runtime._validate_manifest_and_weights()

    assert manifest["model_version"] == "test-model-1"
    assert weights_path.name == "best.pt"
    assert runtime.model_version == "test-model-1"


def test_invalid_checksum_reports_not_ready(tmp_path):
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path, checksum="0" * 64))

    ready, message = runtime.is_ready()

    assert ready is False
    assert "checksum" in message.lower()


def test_missing_weights_reports_model_missing(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "model_version": "test-model-1",
                "detector": {"weights_path": "missing.pt", "plate_class": "plate"},
            }
        ),
        encoding="utf-8",
    )
    runtime = UltralyticsPaddleALPRRuntime(str(manifest_path))

    with pytest.raises(ALPRModelMissingError):
        runtime._ensure_loaded()


def test_ocr_candidates_support_paddleocr_v3_shape():
    output: list[tuple[str, float]] = []

    UltralyticsPaddleALPRRuntime._collect_ocr_candidates(
        [{"rec_texts": ["29A-123.45"], "rec_scores": [0.91]}], output
    )

    assert output == [("29A-123.45", 0.91)]


def test_detector_only_does_not_initialize_ocr(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {0: "plate"}

        def __init__(self, weights_path):
            self.weights_path = weights_path

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path), ocr_enabled=False)

    ready, message = runtime.is_ready()

    assert ready is True
    assert "detector-only" in message
    assert runtime._ocr is None


def test_detector_only_returns_best_clamped_plate_bbox(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {0: "plate", 1: "vehicle"}
        instances = 0
        predictions = 0

        def __init__(self, weights_path):
            self.weights_path = weights_path
            type(self).instances += 1

        def predict(self, **kwargs):
            type(self).predictions += 1
            return [
                FakePrediction(
                    FakeBoxes(
                        classes=[[1], [0], [0]],
                        confidences=[[0.99], [0.90], [0.70]],
                        coordinates=[
                            [0, 0, 12, 8],
                            [-5, 2, 20, 30],
                            [1, 1, 4, 4],
                        ],
                    )
                )
            ]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path), ocr_enabled=False)

    first = runtime.detect_and_read(image_bytes())
    second = runtime.detect_and_read(image_bytes())

    assert first.plate_number is None
    assert first.bbox is not None
    assert first.bbox.model_dump() == {"x1": 0, "y1": 2, "x2": 12, "y2": 8}
    assert first.confidence == 0.90
    assert first.requires_confirmation is True
    assert first.processing_time_ms >= 0
    assert second.bbox == first.bbox
    assert FakeYOLO.instances == 1
    assert FakeYOLO.predictions == 2


def test_detector_returns_no_plate_without_exception(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {1: "vehicle"}

        def __init__(self, weights_path):
            self.weights_path = weights_path

        def predict(self, **kwargs):
            return [FakePrediction(FakeBoxes([[1]], [[0.99]], [[1, 1, 4, 4]]))]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path), ocr_enabled=False)

    result = runtime.detect_and_read(image_bytes())

    assert result.plate_number is None
    assert result.bbox is None
    assert result.confidence == 0.0
    assert result.requires_confirmation is True


def test_detector_inference_error_is_typed(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {0: "plate"}

        def __init__(self, weights_path):
            self.weights_path = weights_path

        def predict(self, **kwargs):
            raise RuntimeError("fake detector failure")

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path), ocr_enabled=False)

    with pytest.raises(ALPRInferenceError, match="Detector inference failed"):
        runtime.detect_and_read(image_bytes())


def test_detector_and_recognition_provider_returns_normalized_plate(tmp_path, monkeypatch):
    class FakeYOLO:
        names = {0: "plate"}

        def __init__(self, weights_path):
            pass

        def predict(self, **kwargs):
            return [FakePrediction(FakeBoxes([[0]], [[0.96]], [[20, 20, 220, 70]]))]

    class FakeOCR:
        def __init__(self, **kwargs):
            pass

        def ensure_loaded(self):
            pass

        def recognize(self, crop):
            assert crop.shape[1] > crop.shape[0]
            return OCRReadResult("30A-123.45", "30A12345", 0.93)

    image = np.random.default_rng(4).integers(40, 220, size=(120, 280, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))
    monkeypatch.setattr("app.alpr.pt_provider.PaddleOCRTextRecognition", FakeOCR)
    runtime = UltralyticsPaddleALPRRuntime(write_manifest(tmp_path), ocr_enabled=True)

    result = runtime.detect_and_read(encoded.tobytes())

    assert result.plate_number == "30A12345"
    assert result.raw_plate == "30A-123.45"
    assert result.normalized_plate == "30A12345"
    assert result.detector_confidence == 0.96
    assert result.ocr_confidence == 0.93
    assert result.combined_confidence == 0.93
    assert result.quality_flags == []
