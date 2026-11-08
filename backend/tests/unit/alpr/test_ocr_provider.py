import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.alpr.errors import ALPRInferenceError, ALPRModelLoadError
from app.alpr.ocr_provider import PaddleOCRTextRecognition


def test_collect_candidates_supports_scalar_and_array_shapes():
    output: list[tuple[str, float]] = []
    PaddleOCRTextRecognition.collect_candidates(
        {
            "rec_text": "30A-123.45",
            "rec_score": 0.91,
        },
        output,
    )
    PaddleOCRTextRecognition.collect_candidates(
        [{"rec_texts": ["51F 12345"], "rec_scores": [0.82]}], output
    )

    assert output == [("30A-123.45", 0.91), ("51F 12345", 0.82)]


def test_recognition_model_is_lazy_loaded_and_normalizes_text(monkeypatch):
    class FakeTextRecognition:
        instances = 0

        def __init__(self, **kwargs):
            type(self).instances += 1
            assert kwargs["model_name"] == "latin_PP-OCRv5_mobile_rec"

        def predict(self, **kwargs):
            assert kwargs["batch_size"] == 1
            return [{"rec_texts": ["29A-123.45"], "rec_scores": [0.94]}]

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=FakeTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    image = np.zeros((32, 128, 3), dtype=np.uint8)

    first = provider.recognize(image)
    second = provider.recognize(image)

    assert first.raw_text == "29A-123.45"
    assert first.normalized_text == "29A12345"
    assert first.confidence == 0.94
    assert second == first
    assert FakeTextRecognition.instances == 1


def test_model_load_and_inference_errors_are_typed(monkeypatch):
    class BrokenTextRecognition:
        def __init__(self, **kwargs):
            raise RuntimeError("download failed")

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=BrokenTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    with pytest.raises(ALPRModelLoadError):
        provider.ensure_loaded()

    class FailingTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            raise RuntimeError("ocr failed")

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=FailingTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    with pytest.raises(ALPRInferenceError):
        provider.recognize(np.zeros((32, 128, 3), dtype=np.uint8))


def test_two_line_square_plate_splits_and_combines(monkeypatch):
    calls = []

    class TwoLineTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            crop = kwargs.get("input")
            h, w = crop.shape[:2]
            calls.append((h, w))
            # First call is line 1 (upper half)
            if len(calls) == 1:
                return [{"rec_texts": ["29-A1"], "rec_scores": [0.92]}]
            # Second call is line 2 (lower half)
            return [{"rec_texts": ["123.45"], "rec_scores": [0.96]}]

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=TwoLineTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    # Aspect ratio: 80 / 64 = 1.25 <= 2.0 (two-line square plate)
    image = np.zeros((64, 80, 3), dtype=np.uint8)

    result = provider.recognize(image)

    assert len(calls) == 2
    assert result.raw_text == "29-A1 123.45"
    assert result.normalized_text == "29A112345"
    assert round(result.confidence, 4) == 0.94


def test_two_line_square_plate_falls_back_when_split_fails(monkeypatch):
    calls = []

    class FallbackTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            crop = kwargs.get("input")
            h, w = crop.shape[:2]
            calls.append((h, w))
            # Line 1 returns text, but line 2 fails/empty
            if len(calls) == 1:
                return [{"rec_texts": ["29-A1"], "rec_scores": [0.90]}]
            if len(calls) == 2:
                return []
            # Third call is the fallback on full crop
            return [{"rec_texts": ["29A1 12345"], "rec_scores": [0.88]}]

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=FallbackTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    image = np.zeros((64, 80, 3), dtype=np.uint8)

    result = provider.recognize(image)

    assert len(calls) == 3
    assert result.raw_text == "29A1 12345"
    assert result.normalized_text == "29A112345"
    assert round(result.confidence, 4) == 0.88
