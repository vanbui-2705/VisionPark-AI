"""Real ALPR runtime for the trained Ultralytics detector plus pretrained OCR."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from .errors import (
    ALPRChecksumMismatchError,
    ALPRDependencyError,
    ALPRInferenceError,
    ALPRInvalidImageError,
    ALPRManifestError,
    ALPRModelLoadError,
    ALPRModelMissingError,
    ALPRNotReadyError,
    ALPRProcessingError,
)
from .interface import ALPRRuntime
from .ocr_provider import OCRReadResult, PaddleOCRTextRecognition
from .schema import ALPRResult, BoundingBox
from .utils import clamp_bbox, crop_with_quality, decode_image, requires_confirmation

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class UltralyticsPaddleALPRRuntime(ALPRRuntime):
    """Run plate detection with ``best.pt`` and optionally OCR on the crop.

    Heavy dependencies are imported lazily so unit tests do not require
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
        self._load_error: ALPRNotReadyError | None = None
        self._inference_lock = threading.Lock()

        try:
            self._manifest = self._read_manifest()
            self.version = str(self._manifest.get("model_version", self.version))
        except ALPRNotReadyError as exc:
            self._load_error = exc
        except Exception as exc:
            self._load_error = ALPRManifestError(str(exc))

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
            raise ALPRModelMissingError(f"Model manifest not found: {self.manifest_path}")
        try:
            with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ALPRManifestError(f"Could not read model manifest: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ALPRManifestError("Model manifest must be a JSON object")
        if not manifest.get("model_version"):
            raise ALPRManifestError("Model manifest is missing model_version")
        return manifest

    def _resolve_weights_path(self, manifest: dict[str, Any]) -> Path:
        detector = manifest.get("detector", {})
        raw_path = detector.get("weights_path") or manifest.get("weights_path")
        if not raw_path:
            raise ALPRManifestError("Model manifest is missing detector weights_path")
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
            raise ALPRModelMissingError(f"Model weights not found: {weights_path}")

        expected_hash = manifest.get("detector", {}).get("sha256") or manifest.get("sha256")
        if expected_hash:
            digest = hashlib.sha256(weights_path.read_bytes()).hexdigest().upper()
            if digest != str(expected_hash).upper():
                raise ALPRChecksumMismatchError(
                    "Model weights checksum does not match the manifest"
                )
        return manifest, weights_path

    def _create_ocr(self, manifest: dict[str, Any]) -> PaddleOCRTextRecognition:
        config = manifest.get("ocr", {})
        return PaddleOCRTextRecognition(
            model_name=str(config.get("model_name", "latin_PP-OCRv5_mobile_rec")),
            device=self.device,
            model_dir=(
                str(self._resolve_path(config["model_dir"])) if config.get("model_dir") else None
            ),
        )

    def _ensure_loaded(self) -> None:
        if self._model is not None and (not self.ocr_enabled or self._ocr is not None):
            return
        if self._load_error:
            raise self._load_error

        try:
            manifest, weights_path = self._validate_manifest_and_weights()
        except ALPRNotReadyError:
            raise
        except Exception as exc:
            raise ALPRManifestError(str(exc)) from exc
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ALPRDependencyError(
                "Real detector dependency is missing; install backend[real]."
            ) from exc

        try:
            self._model = YOLO(str(weights_path))
            self._ocr = self._create_ocr(manifest) if self.ocr_enabled else None
            if self._ocr is not None:
                self._ocr.ensure_loaded()
            self.version = str(manifest["model_version"])
        except ALPRNotReadyError:
            self._model = None
            self._ocr = None
            raise
        except Exception as exc:
            self._model = None
            self._ocr = None
            raise ALPRModelLoadError(f"Could not load real ALPR models: {exc}") from exc

    def is_ready(self) -> tuple[bool, str]:
        try:
            self._ensure_loaded()
        except ALPRNotReadyError as exc:
            return False, str(exc)
        mode = "detector + OCR" if self.ocr_enabled else "detector-only"
        return True, f"Loaded {mode} model {self.model_version}"

    def warmup(self) -> tuple[bool, str]:
        """Initialize inference kernels without recording any synthetic detection."""
        ready, message = self.is_ready()
        if not ready:
            return ready, message
        try:
            import numpy as np

            with self._inference_lock:
                self._model.predict(
                    source=np.zeros((640, 640, 3), dtype=np.uint8),
                    imgsz=640,
                    conf=self.detector_confidence,
                    device=self.device,
                    verbose=False,
                )
                if self._ocr:
                    self._ocr.recognize(np.full((48, 320, 3), 255, dtype=np.uint8))
            return True, message
        except Exception as exc:
            self._model = None
            self._ocr = None
            self._load_error = ALPRModelLoadError(f"Model warmup failed: {type(exc).__name__}")
            return False, str(self._load_error)

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
        if boxes is None or len(boxes) == 0:
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
            raw_coordinates = boxes.xyxy[index]
            coordinates = (
                raw_coordinates.tolist()
                if hasattr(raw_coordinates, "tolist")
                else list(raw_coordinates)
            )
            if len(coordinates) != 4:
                continue
            bbox = BoundingBox(
                x1=int(coordinates[0]),
                y1=int(coordinates[1]),
                x2=int(coordinates[2]),
                y2=int(coordinates[3]),
            )
            if confidence > best[1]:
                best = (bbox, confidence)
        return best

    @classmethod
    def _collect_ocr_candidates(cls, value: Any, output: list[tuple[str, float]]) -> None:
        PaddleOCRTextRecognition.collect_candidates(value, output)

    def _run_ocr(self, crop: Any) -> OCRReadResult:
        if self._ocr is None:
            return OCRReadResult(None, None, 0.0)
        return self._ocr.recognize(crop)

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        started = time.perf_counter()
        try:
            self._ensure_loaded()
            image = decode_image(image_bytes)
            with self._inference_lock:
                detector_started = time.perf_counter()
                try:
                    predictions = self._model.predict(
                        source=image,
                        imgsz=int(self._manifest.get("detector", {}).get("imgsz", 640)),
                        conf=self.detector_confidence,
                        device=self.device,
                        verbose=False,
                    )
                except Exception as exc:
                    raise ALPRInferenceError(f"Detector inference failed: {exc}") from exc

                prediction = predictions[0] if predictions else None
                bbox, detector_confidence = self._find_plate(prediction)
                detector_latency_ms = (time.perf_counter() - detector_started) * 1000
                if bbox is None:
                    return ALPRResult(
                        plate_number=None,
                        bbox=None,
                        confidence=0.0,
                        processing_time_ms=int((time.perf_counter() - started) * 1000),
                        requires_confirmation=True,
                        model_version=self.model_version,
                        detector_confidence=0.0,
                        combined_confidence=0.0,
                        provider="ultralytics-paddleocr",
                        detector_latency_ms=detector_latency_ms,
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
                        detector_confidence=detector_confidence,
                        combined_confidence=0.0,
                        provider="ultralytics-paddleocr",
                        detector_latency_ms=detector_latency_ms,
                    )
                bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                quality_flags: list[str] = []
                ocr_latency_ms: float | None = None
                if self.ocr_enabled:
                    ocr_started = time.perf_counter()
                    crop, _, quality_flags = crop_with_quality(
                        image, bbox.as_tuple, margin=self.ocr_margin
                    )
                    if quality_flags:
                        quality_flags.append("ocr_skipped_quality")
                        plate_result = OCRReadResult(None, None, 0.0)
                    else:
                        plate_result = self._run_ocr(crop)
                    ocr_latency_ms = (time.perf_counter() - ocr_started) * 1000
                    plate = plate_result.normalized_text
                    raw_plate = plate_result.raw_text
                    ocr_confidence = plate_result.confidence
                else:
                    plate, raw_plate, ocr_confidence = None, None, None

            if not plate:
                confidence = detector_confidence if not self.ocr_enabled else 0.0
                return ALPRResult(
                    plate_number=None,
                    raw_plate=raw_plate,
                    normalized_plate=None,
                    bbox=bbox,
                    confidence=confidence,
                    processing_time_ms=int((time.perf_counter() - started) * 1000),
                    requires_confirmation=True,
                    model_version=self.model_version,
                    detector_confidence=detector_confidence,
                    ocr_confidence=ocr_confidence,
                    combined_confidence=confidence,
                    quality_flags=quality_flags,
                    provider="ultralytics-paddleocr",
                    detector_latency_ms=detector_latency_ms,
                    ocr_latency_ms=ocr_latency_ms,
                )

            confidence = min(detector_confidence, ocr_confidence)
            return ALPRResult(
                plate_number=plate,
                raw_plate=raw_plate,
                normalized_plate=plate,
                bbox=bbox,
                confidence=confidence,
                processing_time_ms=int((time.perf_counter() - started) * 1000),
                requires_confirmation=requires_confirmation(
                    confidence, self.confirmation_threshold
                ),
                model_version=self.model_version,
                detector_confidence=detector_confidence,
                ocr_confidence=ocr_confidence,
                combined_confidence=confidence,
                quality_flags=quality_flags,
                provider="ultralytics-paddleocr",
                detector_latency_ms=detector_latency_ms,
                ocr_latency_ms=ocr_latency_ms,
            )
        except (ALPRInvalidImageError, ALPRNotReadyError, ALPRProcessingError):
            raise
        except Exception as exc:
            raise ALPRProcessingError(f"Real ALPR inference failed: {exc}") from exc
