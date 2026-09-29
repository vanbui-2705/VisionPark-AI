"""Real ALPR runtime for the trained Ultralytics detector plus pretrained OCR."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from .errors import ALPRNotReadyError, ALPRProcessingError
from .interface import ALPRRuntime
from .schema import ALPRResult, BoundingBox
from .utils import clamp_bbox, crop_plate, decode_image, normalize_plate, requires_confirmation

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class UltralyticsPaddleALPRRuntime(ALPRRuntime):
    """Run plate detection with ``best.pt`` and optionally OCR on the crop.

    Heavy dependencies are imported lazily so mock mode and CI do not require
    PyTorch, Ultralytics, PaddleOCR, or a model weight.
    """

    def __init__(
        self,
        manifest_path: str,
        *,
        device: str = "cpu",
        detector_confidence: float = 0.25,
        confirmation_threshold: float = 0.85,
        ocr_margin: float = 0.08,
        ocr_enabled: bool = False,
    ) -> None:
        self.manifest_path = self._resolve_path(manifest_path)
        self.device = device
        self.detector_confidence = detector_confidence
        self.confirmation_threshold = confirmation_threshold
        self.ocr_margin = ocr_margin
        self.ocr_enabled = ocr_enabled
        self.version = "real-unloaded"
        self._manifest: dict[str, Any] | None = None
        self._model: Any = None
        self._ocr: Any = None
        self._load_error: str | None = None
        self._inference_lock = threading.Lock()

        try:
            self._manifest = self._read_manifest()
            self.version = str(self._manifest.get("model_version", self.version))
        except Exception as exc:
            self._load_error = str(exc)

    @property
    def model_version(self) -> str:
        return self.version

    @staticmethod
    def _resolve_path(path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        candidates = (Path.cwd() / path, BACKEND_ROOT / path)
        return next((candidate for candidate in candidates if candidate.exists()), candidates[-1])

    def _read_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"Model manifest not found: {self.manifest_path}")
        with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
        if not isinstance(manifest, dict):
            raise ValueError("Model manifest must be a JSON object")
        if not manifest.get("model_version"):
            raise ValueError("Model manifest is missing model_version")
        return manifest

    def _resolve_weights_path(self, manifest: dict[str, Any]) -> Path:
        detector = manifest.get("detector", {})
        raw_path = detector.get("weights_path") or manifest.get("weights_path")
        if not raw_path:
            raise ValueError("Model manifest is missing detector weights_path")
        path = Path(raw_path)
        if path.is_absolute():
            return path
        candidates = (
            self.manifest_path.parent / path,
            self.manifest_path.parent.parent / path,
            BACKEND_ROOT / path,
        )
        return next((candidate for candidate in candidates if candidate.exists()), candidates[-1])

    def _validate_manifest_and_weights(self) -> tuple[dict[str, Any], Path]:
        manifest = self._manifest or self._read_manifest()
        weights_path = self._resolve_weights_path(manifest)
        if not weights_path.is_file():
            raise FileNotFoundError(f"Model weights not found: {weights_path}")

        expected_hash = manifest.get("detector", {}).get("sha256") or manifest.get("sha256")
        if expected_hash:
            digest = hashlib.sha256(weights_path.read_bytes()).hexdigest().upper()
            if digest != str(expected_hash).upper():
                raise ValueError("Model weights checksum does not match the manifest")
        return manifest, weights_path

    def _create_ocr(self, paddle_ocr: Any) -> Any:
        try:
            return paddle_ocr(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except TypeError:
            # PaddleOCR 2.x compatibility.
            return paddle_ocr(use_angle_cls=False, lang="en", show_log=False)

    def _ensure_loaded(self) -> None:
        if self._model is not None and (not self.ocr_enabled or self._ocr is not None):
            return
        if self._load_error:
            raise ALPRNotReadyError(self._load_error)

        try:
            manifest, weights_path = self._validate_manifest_and_weights()
        except Exception as exc:
            raise ALPRNotReadyError(str(exc)) from exc
        try:
            from ultralytics import YOLO

            paddle_ocr = None
            if self.ocr_enabled:
                from paddleocr import PaddleOCR

                paddle_ocr = PaddleOCR
        except ImportError as exc:
            raise ALPRNotReadyError(
                "Real detector dependency is missing; install backend[real]."
            ) from exc

        try:
            self._model = YOLO(str(weights_path))
            self._ocr = self._create_ocr(paddle_ocr) if self.ocr_enabled else None
            self.version = str(manifest["model_version"])
        except Exception as exc:
            self._model = None
            self._ocr = None
            raise ALPRNotReadyError(f"Could not load real ALPR models: {exc}") from exc

    def is_ready(self) -> tuple[bool, str]:
        try:
            self._ensure_loaded()
        except ALPRNotReadyError as exc:
            return False, str(exc)
        mode = "detector + OCR" if self.ocr_enabled else "detector-only"
        return True, f"Loaded {mode} model {self.model_version}"

    @staticmethod
    def _scalar(value: Any) -> float:
        if hasattr(value, "item"):
            return float(value.item())
        if isinstance(value, (list, tuple)):
            return float(value[0])
        return float(value)

    def _find_plate(self, prediction: Any) -> tuple[BoundingBox | None, float]:
        boxes = getattr(prediction, "boxes", None)
        names = getattr(self._model, "names", {})
        if boxes is None:
            return None, 0.0

        best: tuple[BoundingBox | None, float] = (None, 0.0)
        plate_class_name = (
            str(self._manifest.get("detector", {}).get("plate_class", "plate"))
            if self._manifest
            else "plate"
        )
        for index in range(len(boxes)):
            class_id = int(self._scalar(boxes.cls[index]))
            label = names.get(class_id, str(class_id)) if isinstance(names, dict) else str(class_id)
            if str(label).casefold() != plate_class_name.casefold():
                continue
            confidence = self._scalar(boxes.conf[index])
            coordinates = boxes.xyxy[index].tolist()
            bbox = BoundingBox(
                x1=int(coordinates[0]),
                y1=int(coordinates[1]),
                x2=int(coordinates[2]),
                y2=int(coordinates[3]),
            )
            if confidence > best[1]:
                best = (bbox, confidence)
        return best

    def _crop_with_margin(self, image: Any, bbox: BoundingBox) -> Any:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = bbox.as_tuple
        margin_x = int((x2 - x1) * self.ocr_margin)
        margin_y = int((y2 - y1) * self.ocr_margin)
        expanded = clamp_bbox(
            (x1 - margin_x, y1 - margin_y, x2 + margin_x, y2 + margin_y),
            width,
            height,
        )
        return crop_plate(image, expanded)

    @classmethod
    def _collect_ocr_candidates(cls, value: Any, output: list[tuple[str, float]]) -> None:
        if value is None:
            return
        if hasattr(value, "json"):
            payload = value.json
            payload = payload() if callable(payload) else payload
            if isinstance(payload, str):
                payload = json.loads(payload)
            cls._collect_ocr_candidates(payload, output)
            return
        if isinstance(value, dict):
            texts = value.get("rec_texts") or value.get("texts")
            scores = value.get("rec_scores") or value.get("scores") or []
            if texts:
                for index, text in enumerate(texts):
                    score = scores[index] if index < len(scores) else 0.0
                    output.append((str(text), float(score)))
                return
            for item in value.values():
                cls._collect_ocr_candidates(item, output)
            return
        if isinstance(value, (list, tuple)):
            if len(value) == 2 and isinstance(value[0], str):
                output.append((value[0], float(value[1])))
                return
            for item in value:
                cls._collect_ocr_candidates(item, output)

    def _run_ocr(self, crop: Any) -> tuple[str | None, float]:
        if crop is None or getattr(crop, "size", 0) == 0:
            return None, 0.0
        if hasattr(self._ocr, "predict"):
            raw_result = list(self._ocr.predict(crop))
        else:
            raw_result = self._ocr.ocr(crop, cls=False)
        candidates: list[tuple[str, float]] = []
        self._collect_ocr_candidates(raw_result, candidates)
        if not candidates:
            return None, 0.0
        text, confidence = max(candidates, key=lambda item: item[1])
        normalized = normalize_plate(text)
        return (normalized or None), max(0.0, min(1.0, confidence))

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        started = time.perf_counter()
        try:
            self._ensure_loaded()
            image = decode_image(image_bytes)
            if image is None:
                raise ValueError("Could not decode input frame")
            with self._inference_lock:
                predictions = self._model.predict(
                    source=image,
                    imgsz=int(self._manifest.get("detector", {}).get("imgsz", 640)),
                    conf=self.detector_confidence,
                    device=self.device,
                    verbose=False,
                )
                bbox, detector_confidence = self._find_plate(predictions[0])
                if bbox is None:
                    return ALPRResult(
                        plate_number=None,
                        bbox=None,
                        confidence=0.0,
                        processing_time_ms=int((time.perf_counter() - started) * 1000),
                        requires_confirmation=True,
                        model_version=self.model_version,
                    )
                x1, y1, x2, y2 = clamp_bbox(bbox.as_tuple, image.shape[1], image.shape[0])
                if x2 <= x1 or y2 <= y1:
                    return ALPRResult(
                        plate_number=None,
                        bbox=None,
                        confidence=0.0,
                        processing_time_ms=int((time.perf_counter() - started) * 1000),
                        requires_confirmation=True,
                        model_version=self.model_version,
                    )
                bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                if self.ocr_enabled:
                    plate, ocr_confidence = self._run_ocr(self._crop_with_margin(image, bbox))
                else:
                    plate, ocr_confidence = None, 0.0

            if not plate:
                confidence = detector_confidence
                return ALPRResult(
                    plate_number=None,
                    bbox=bbox,
                    confidence=confidence,
                    processing_time_ms=int((time.perf_counter() - started) * 1000),
                    requires_confirmation=True,
                    model_version=self.model_version,
                )

            confidence = min(detector_confidence, ocr_confidence)
            return ALPRResult(
                plate_number=plate,
                bbox=bbox,
                confidence=confidence,
                processing_time_ms=int((time.perf_counter() - started) * 1000),
                requires_confirmation=requires_confirmation(
                    confidence, self.confirmation_threshold
                ),
                model_version=self.model_version,
            )
        except (ALPRNotReadyError, ALPRProcessingError):
            raise
        except Exception as exc:
            raise ALPRProcessingError(f"Real ALPR inference failed: {exc}") from exc
