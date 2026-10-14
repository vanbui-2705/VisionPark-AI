"""Small PaddleOCR text-recognition adapter used by the ALPR runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from .errors import (
    ALPRDependencyError,
    ALPRInferenceError,
    ALPRModelLoadError,
    ALPRNotReadyError,
    ALPROCRTimeoutError,
)
from .utils import normalize_plate


@dataclass(frozen=True)
class OCRReadResult:
    raw_text: str | None
    normalized_text: str | None
    confidence: float


class PaddleOCRTextRecognition:
    """Lazy, recognition-only PaddleOCR provider for detector-generated crops."""

    def __init__(
        self,
        *,
        model_name: str = "latin_PP-OCRv5_mobile_rec",
        device: str = "cpu",
        model_dir: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.model_dir = model_dir
        self._model: Any = None

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from paddleocr import TextRecognition
        except ImportError as exc:
            raise ALPRDependencyError("OCR dependency is missing; install backend[ocr].") from exc
        try:
            kwargs: dict[str, Any] = {"model_name": self.model_name, "device": self.device}
            if self.model_dir:
                kwargs["model_dir"] = self.model_dir
            self._model = TextRecognition(**kwargs)
        except Exception as exc:
            raise ALPRModelLoadError(f"Could not load OCR model: {exc}") from exc

    def is_ready(self) -> tuple[bool, str]:
        try:
            self.ensure_loaded()
        except ALPRNotReadyError as exc:
            return False, str(exc)
        return True, f"Loaded OCR model {self.model_name}"

    @classmethod
    def collect_candidates(cls, value: Any, output: list[tuple[str, float]]) -> None:
        """Extract text/score pairs from PaddleOCR v2/v3 result shapes."""
        if value is None:
            return
        if hasattr(value, "json"):
            payload = value.json
            payload = payload() if callable(payload) else payload
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    return
            cls.collect_candidates(payload, output)
            return
        if isinstance(value, dict):
            text = value.get("rec_text") or value.get("text")
            score = value.get("rec_score") or value.get("score")
            if text is not None:
                output.append((str(text), float(score or 0.0)))
                return
            texts = value.get("rec_texts") or value.get("texts")
            scores = value.get("rec_scores") or value.get("scores") or []
            if texts:
                for index, item in enumerate(texts):
                    confidence = scores[index] if index < len(scores) else 0.0
                    output.append((str(item), float(confidence)))
                return
            for item in value.values():
                cls.collect_candidates(item, output)
            return
        if isinstance(value, list | tuple):
            if len(value) == 2 and isinstance(value[0], str):
                output.append((value[0], float(value[1])))
                return
            for item in value:
                cls.collect_candidates(item, output)

    def _recognize_crop(self, crop: np.ndarray) -> OCRReadResult:
        try:
            try:
                raw_result = list(self._model.predict(input=crop, batch_size=1))
            except TypeError:
                raw_result = list(self._model.predict(crop))
        except TimeoutError as exc:
            raise ALPROCRTimeoutError(f"OCR inference timed out: {exc}") from exc
        except Exception as exc:
            raise ALPRInferenceError(f"OCR inference failed: {exc}") from exc
        candidates: list[tuple[str, float]] = []
        self.collect_candidates(raw_result, candidates)
        if not candidates:
            return OCRReadResult(None, None, 0.0)

        # Support 2-line square motorbike plates (Vietnamese standard)
        if len(candidates) > 1:
            combined_raw = " ".join(item[0].strip() for item in candidates if item[0].strip())
            combined_norm = normalize_plate(combined_raw)
            if 6 <= len(combined_norm) <= 10:
                avg_conf = sum(item[1] for item in candidates) / len(candidates)
                bounded_conf = max(0.0, min(1.0, float(avg_conf)))
                return OCRReadResult(combined_raw, combined_norm, bounded_conf)

        raw_text, confidence = max(candidates, key=lambda item: item[1])
        normalized = normalize_plate(raw_text) or None
        bounded_confidence = max(0.0, min(1.0, float(confidence)))
        return OCRReadResult(raw_text, normalized, bounded_confidence)

    def recognize(self, crop: np.ndarray) -> OCRReadResult:
        if crop is None or getattr(crop, "size", 0) == 0:
            return OCRReadResult(None, None, 0.0)
        self.ensure_loaded()
        full_result = self._recognize_crop(crop)
        height, width = crop.shape[:2]
        if height < 16 or width / height >= 1.8:
            return full_result

        # The recognition-only model expects one text row. For a near-square Vietnamese
        # plate, recognize both physical rows and preserve their top-to-bottom order.
        overlap = max(1, int(height * 0.04))
        midpoint = height // 2
        top_result = self._recognize_crop(crop[: midpoint + overlap])
        bottom_result = self._recognize_crop(crop[midpoint - overlap :])
        if not top_result.normalized_text or not bottom_result.normalized_text:
            return full_result
        combined = top_result.normalized_text + bottom_result.normalized_text
        if not 6 <= len(combined) <= 10:
            return full_result
        return OCRReadResult(
            raw_text=f"{top_result.raw_text}\n{bottom_result.raw_text}",
            normalized_text=combined,
            confidence=min(top_result.confidence, bottom_result.confidence),
        )
