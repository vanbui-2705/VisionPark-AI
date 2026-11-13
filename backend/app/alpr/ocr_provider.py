"""Small PaddleOCR text-recognition adapter used by the ALPR runtime."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import cv2
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


@dataclass(frozen=True)
class OCRCandidate:
    """One recognition result produced from a named image variant."""

    raw_text: str
    confidence: float
    source: str


def select_plate_candidate(candidates: list[OCRCandidate]) -> OCRReadResult:
    """Choose the plate supported by the most independent image variants."""
    grouped: dict[str, list[OCRCandidate]] = {}
    for candidate in candidates:
        normalized = normalize_plate(candidate.raw_text)
        if not _looks_like_vietnamese_plate(normalized):
            continue
        grouped.setdefault(normalized, []).append(candidate)

    if not grouped:
        return OCRReadResult(None, None, 0.0)

    normalized, agreeing = max(
        grouped.items(),
        key=lambda item: (
            len(item[1]),
            sum(candidate.confidence for candidate in item[1]) / len(item[1]),
            max(candidate.confidence for candidate in item[1]),
        ),
    )
    best = max(agreeing, key=lambda candidate: candidate.confidence)
    return OCRReadResult(
        best.raw_text,
        normalized,
        max(0.0, min(1.0, float(best.confidence))),
    )


def _looks_like_vietnamese_plate(normalized: str | None) -> bool:
    if not normalized:
        return False
    return bool(re.fullmatch(r"\d{2}[A-Z][A-Z0-9]?\d{4,5}", normalized))


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

    def _predict_single_crop(self, crop: np.ndarray) -> list[tuple[str, float]]:
        """Predict text and scores for a single image crop."""
        if crop is None or getattr(crop, "size", 0) == 0:
            return []
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
        return candidates

    def _append_candidates(
        self,
        output: list[OCRCandidate],
        crop: np.ndarray,
        source: str,
    ) -> list[tuple[str, float]]:
        predictions = self._predict_single_crop(crop)
        output.extend(
            OCRCandidate(text.strip(), float(confidence), source)
            for text, confidence in predictions
            if text and text.strip()
        )
        return predictions

    @staticmethod
    def _clahe(crop: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    def recognize(self, crop: np.ndarray) -> OCRReadResult:
        if crop is None or getattr(crop, "size", 0) == 0:
            return OCRReadResult(None, None, 0.0)
        self.ensure_loaded()
        h, w = crop.shape[:2]
        candidates: list[OCRCandidate] = []
        full_predictions = self._append_candidates(candidates, crop, "original")

        if full_predictions:
            raw_text, confidence = max(full_predictions, key=lambda item: item[1])
            normalized = normalize_plate(raw_text)
            if confidence >= 0.90 and _looks_like_vietnamese_plate(normalized):
                return OCRReadResult(raw_text, normalized, min(1.0, float(confidence)))

        enhanced = self._clahe(crop)

        # A detector box can be almost square either because the physical plate
        # has two rows or because a distant single-row plate includes vertical
        # padding. Evaluate both interpretations and let consensus decide.
        if h >= 20 and w > 0 and (w / h) <= 2.2:
            for source, variant in (("original", crop), ("clahe", enhanced)):
                top = variant[0 : max(1, int(h * 0.59)), :]
                bottom = variant[min(h - 1, int(h * 0.45)) : h, :]
                top_predictions = self._append_candidates(candidates, top, f"{source}:top")
                bottom_predictions = self._append_candidates(
                    candidates, bottom, f"{source}:bottom"
                )
                if top_predictions and bottom_predictions:
                    top_text, top_confidence = max(
                        top_predictions, key=lambda item: item[1]
                    )
                    bottom_text, bottom_confidence = max(
                        bottom_predictions, key=lambda item: item[1]
                    )
                    candidates.append(
                        OCRCandidate(
                            f"{top_text.strip()} {bottom_text.strip()}",
                            (float(top_confidence) + float(bottom_confidence)) / 2.0,
                            f"{source}:combined",
                        )
                    )

        # For low-confidence one-row crops, trimming detector padding and
        # enhancing local contrast recovered characters without changing model
        # weights. Keep this to one extra inference to bound latency.
        tight_height = max(1, int(h * 0.62))
        self._append_candidates(candidates, enhanced[:tight_height, :], "clahe:tight")

        selected = select_plate_candidate(candidates)
        if selected.normalized_text:
            return selected

        if not full_predictions:
            return OCRReadResult(None, None, 0.0)
        raw_text, confidence = max(full_predictions, key=lambda item: item[1])
        return OCRReadResult(
            raw_text,
            normalize_plate(raw_text) or None,
            max(0.0, min(1.0, float(confidence))),
        )
