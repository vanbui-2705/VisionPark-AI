import hashlib
import json
import sys
from types import SimpleNamespace

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
