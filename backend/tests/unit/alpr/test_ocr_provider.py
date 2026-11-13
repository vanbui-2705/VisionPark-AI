import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.alpr.errors import ALPRInferenceError, ALPRModelLoadError
from app.alpr.ocr_provider import OCRCandidate, PaddleOCRTextRecognition, select_plate_candidate


def _predict_each(input_value, predict_one):
    crops = input_value if isinstance(input_value, list) else [input_value]
    return [predict_one(crop) for crop in crops]


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


def test_candidate_consensus_beats_one_higher_confidence_misread():
    result = select_plate_candidate(
        [
            OCRCandidate("29A-90.01", 0.90, "original"),
            OCRCandidate("29A-901.01", 0.84, "upscaled"),
            OCRCandidate("29A90101", 0.82, "contrast"),
        ]
    )

    assert result.raw_text == "29A-901.01"
    assert result.normalized_text == "29A90101"
    assert result.confidence == 0.84


def test_crops_from_one_preprocessing_family_only_cast_one_vote():
    result = select_plate_candidate(
        [
            OCRCandidate("51B-0392", 0.74, "original:full"),
            OCRCandidate("51B-0392", 0.72, "original:top"),
            OCRCandidate("51B-04392", 0.86, "clahe:tight"),
        ]
    )

    assert result.normalized_text == "51B04392"


def test_five_digit_serial_wins_when_candidate_confidence_is_nearly_tied():
    result = select_plate_candidate(
        [
            OCRCandidate("29A 7952", 0.781, "original:combined"),
            OCRCandidate("29A 74952", 0.763, "clahe:combined"),
        ]
    )

    assert result.normalized_text == "29A74952"


def test_low_confidence_full_crop_uses_a_tighter_preprocessed_candidate(monkeypatch):
    class CropSensitiveTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            def predict_one(crop):
                if crop.shape[0] < 28:
                    return {"rec_texts": ["51B-04392"], "rec_scores": [0.86]}
                return {"rec_texts": ["51B-0392"], "rec_scores": [0.74]}

            return _predict_each(kwargs["input"], predict_one)

    monkeypatch.setitem(
        sys.modules,
        "paddleocr",
        SimpleNamespace(TextRecognition=CropSensitiveTextRecognition),
    )
    provider = PaddleOCRTextRecognition()
    image = np.tile(np.arange(128, dtype=np.uint8), (32, 1))
    image = np.repeat(image[:, :, None], 3, axis=2)

    result = provider.recognize(image)

    assert result.raw_text == "51B-04392"
    assert result.normalized_text == "51B04392"
    assert result.confidence == 0.86


def test_recognition_does_not_short_circuit_on_one_high_confidence_misread(monkeypatch):
    class HighConfidenceMisread:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            def predict_one(crop):
                if crop.shape[0] < 28:
                    return {"rec_texts": ["29A-901.01"], "rec_scores": [0.84]}
                return {"rec_texts": ["29A-90.01"], "rec_scores": [0.90]}

            return _predict_each(kwargs["input"], predict_one)

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=HighConfidenceMisread)
    )
    provider = PaddleOCRTextRecognition()

    result = provider.recognize(np.zeros((32, 128, 3), dtype=np.uint8))

    assert result.normalized_text == "29A90101"


def test_invalid_ocr_text_is_not_published_as_a_plate(monkeypatch):
    class InvalidTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            return _predict_each(
                kwargs["input"],
                lambda crop: {"rec_texts": ["HELLO"], "rec_scores": [0.95]},
            )

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=InvalidTextRecognition)
    )
    provider = PaddleOCRTextRecognition()

    result = provider.recognize(np.zeros((32, 128, 3), dtype=np.uint8))

    assert result.raw_text == "HELLO"
    assert result.normalized_text is None


def test_recognition_model_is_lazy_loaded_and_normalizes_text(monkeypatch):
    class FakeTextRecognition:
        instances = 0

        def __init__(self, **kwargs):
            type(self).instances += 1
            assert kwargs["model_name"] == "latin_PP-OCRv5_mobile_rec"

        def predict(self, **kwargs):
            crops = kwargs["input"] if isinstance(kwargs["input"], list) else [kwargs["input"]]
            assert kwargs["batch_size"] == len(crops)
            return [{"rec_texts": ["29A-123.45"], "rec_scores": [0.94]} for _ in crops]

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
    class TwoLineTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            def predict_one(crop):
                h, _ = crop.shape[:2]
                if h == 64:
                    return {"rec_texts": [], "rec_scores": []}
                if float(crop.mean()) < 125:
                    return {"rec_texts": ["29-A1"], "rec_scores": [0.92]}
                return {"rec_texts": ["123.45"], "rec_scores": [0.96]}

            return _predict_each(kwargs["input"], predict_one)

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=TwoLineTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    # Aspect ratio: 80 / 64 = 1.25 <= 2.0 (two-line square plate)
    image = np.zeros((64, 80, 3), dtype=np.uint8)
    image[:32] = 50
    image[32:] = 200

    result = provider.recognize(image)

    assert result.raw_text == "29-A1 123.45"
    assert result.normalized_text == "29A112345"
    assert round(result.confidence, 4) == 0.94


def test_two_line_square_plate_falls_back_when_split_fails(monkeypatch):
    class FallbackTextRecognition:
        def __init__(self, **kwargs):
            pass

        def predict(self, **kwargs):
            def predict_one(crop):
                h, _ = crop.shape[:2]
                if h == 64:
                    return {"rec_texts": ["29A1 12345"], "rec_scores": [0.88]}
                return {"rec_texts": [], "rec_scores": []}

            return _predict_each(kwargs["input"], predict_one)

    monkeypatch.setitem(
        sys.modules, "paddleocr", SimpleNamespace(TextRecognition=FallbackTextRecognition)
    )
    provider = PaddleOCRTextRecognition()
    image = np.zeros((64, 80, 3), dtype=np.uint8)

    result = provider.recognize(image)

    assert result.raw_text == "29A1 12345"
    assert result.normalized_text == "29A112345"
    assert round(result.confidence, 4) == 0.88
