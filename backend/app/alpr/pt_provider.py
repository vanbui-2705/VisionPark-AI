"""Real ALPR runtime for the trained Ultralytics detector plus pretrained OCR."""

from __future__ import annotations

import hashlib
import json
import math
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
from .schema import ALPRResult, BoundingBox, VehicleType
from .utils import clamp_bbox, crop_with_quality, decode_image, requires_confirmation

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class UltralyticsPaddleALPRRuntime(ALPRRuntime):
    """Run dual vehicle and plate detection with ``plate.onnx`` / ``best.pt`` plus OCR.

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
        if isinstance(value, list | tuple):
            return float(value[0])
        return float(value)

    @classmethod
    def _map_vehicle_type(cls, label: str) -> str:
        folded = str(label).casefold()
        if folded in ("car", "truck", "bus", "van", "automobile"):
            return VehicleType.CAR.value
        if folded in ("motorcycle", "motorbike", "moto", "scooter"):
            return VehicleType.MOTORBIKE.value
        if folded in ("bicycle", "bike", "cyclist"):
            return VehicleType.BICYCLE.value
        return VehicleType.UNKNOWN.value

    def _extract_detections(
        self, prediction: Any, thresholds: dict[str, float]
    ) -> tuple[list[tuple[BoundingBox, float]], list[tuple[BoundingBox, float, str]]]:
        """Extract all valid plate bounding boxes and vehicle bounding boxes."""
        boxes = getattr(prediction, "boxes", None)
        names = getattr(self._model, "names", {})
        if boxes is None or len(boxes) == 0:
            return [], []

        plate_class_name = (
            str(self._manifest.get("detector", {}).get("plate_class", "plate"))
            if self._manifest
            else "plate"
        ).casefold()

        plates: list[tuple[BoundingBox, float]] = []
        vehicles: list[tuple[BoundingBox, float, str]] = []

        for index in range(len(boxes)):
            class_id = int(self._scalar(boxes.cls[index]))
            label = names.get(class_id, str(class_id)) if isinstance(names, dict) else str(class_id)
            label_fold = str(label).casefold()
            confidence = self._scalar(boxes.conf[index])

            raw_coords = boxes.xyxy[index]
            coords = raw_coords.tolist() if hasattr(raw_coords, "tolist") else list(raw_coords)
            if len(coords) != 4:
                continue

            bbox = BoundingBox(
                x1=int(coords[0]),
                y1=int(coords[1]),
                x2=int(coords[2]),
                y2=int(coords[3]),
            )

            if label_fold == plate_class_name:
                min_conf = thresholds.get("plate", self.detector_confidence)
                if confidence >= min_conf:
                    plates.append((bbox, confidence))
            else:
                vehicle_type = self._map_vehicle_type(label_fold)
                # Check specific vehicle threshold
                type_key = label_fold if label_fold in thresholds else vehicle_type.lower()
                min_conf = thresholds.get(type_key, 0.35)
                if confidence >= min_conf:
                    vehicles.append((bbox, confidence, vehicle_type))

        # Sort descending by confidence
        plates.sort(key=lambda item: item[1], reverse=True)
        vehicles.sort(key=lambda item: item[1], reverse=True)
        return plates, vehicles

    @staticmethod
    def _associate_plate_with_vehicle(
        plate_box: BoundingBox, vehicles: list[tuple[BoundingBox, float, str]]
    ) -> tuple[BoundingBox | None, float | None, str]:
        """Find the vehicle that contains or is closest to the given plate."""
        if not vehicles:
            return None, None, VehicleType.UNKNOWN.value

        px1, py1, px2, py2 = plate_box.as_tuple
        plate_area = max(1, (px2 - px1) * (py2 - py1))
        pcx, pcy = (px1 + px2) / 2.0, (py1 + py2) / 2.0

        best_containment: float = 0.0
        best_vehicle: tuple[BoundingBox, float, str] | None = None

        for v_box, v_conf, v_type in vehicles:
            vx1, vy1, vx2, vy2 = v_box.as_tuple
            ix1, iy1 = max(px1, vx1), max(py1, vy1)
            ix2, iy2 = min(px2, vx2), min(py2, vy2)

            if ix2 > ix1 and iy2 > iy1:
                inter_area = (ix2 - ix1) * (iy2 - iy1)
                containment = inter_area / plate_area
                if containment > best_containment:
                    best_containment = containment
                    best_vehicle = (v_box, v_conf, v_type)

        # Containment >= 50% means plate is inside vehicle box
        if best_vehicle is not None and best_containment >= 0.50:
            return best_vehicle[0], best_vehicle[1], best_vehicle[2]

        # Fallback: minimum distance between centers
        closest_vehicle = None
        min_dist = float("inf")
        for v_box, v_conf, v_type in vehicles:
            vx1, vy1, vx2, vy2 = v_box.as_tuple
            vcx, vcy = (vx1 + vx2) / 2.0, (vy1 + vy2) / 2.0
            dist = math.hypot(pcx - vcx, pcy - vcy)
            if dist < min_dist:
                min_dist = dist
                closest_vehicle = (v_box, v_conf, v_type)

        if closest_vehicle is not None:
            return closest_vehicle[0], closest_vehicle[1], closest_vehicle[2]

        return None, None, VehicleType.UNKNOWN.value

    def _find_plate(self, prediction: Any) -> tuple[BoundingBox | None, float]:
        """Legacy helper maintained for test compatibility."""
        plates, _ = self._extract_detections(prediction, {"plate": self.detector_confidence})
        if plates:
            return plates[0]
        return None, 0.0

    @classmethod
    def _collect_ocr_candidates(cls, value: Any, output: list[tuple[str, float]]) -> None:
        PaddleOCRTextRecognition.collect_candidates(value, output)

    def _run_ocr(self, crop: Any) -> OCRReadResult:
        if self._ocr is None:
            return OCRReadResult(None, None, 0.0)
        return self._ocr.recognize(crop)

    def detect_and_read(
        self, image_bytes: bytes, settings: dict[str, Any] | None = None
    ) -> ALPRResult:
        started = time.perf_counter()
        try:
            self._ensure_loaded()
            image = decode_image(image_bytes)

            # Resolve effective thresholds (from dynamic settings or manifest/defaults)
            settings = settings or {}
            manifest_thresh = (
                self._manifest.get("detector", {}).get("confidence_thresholds", {})
                if self._manifest
                else {}
            )
            thresholds: dict[str, float] = {
                "plate": float(
                    settings.get(
                        "plate_confidence", manifest_thresh.get("plate", self.detector_confidence)
                    )
                ),
                "car": float(settings.get("car_confidence", manifest_thresh.get("car", 0.45))),
                "motorcycle": float(
                    settings.get("motorcycle_confidence", manifest_thresh.get("motorcycle", 0.40))
                ),
                "bicycle": float(
                    settings.get("bicycle_confidence", manifest_thresh.get("bicycle", 0.35))
                ),
            }
            confirmation_thresh = float(
                settings.get("confirmation_threshold", self.confirmation_threshold)
            )
            building_id = settings.get("building_id")

            with self._inference_lock:
                detector_started = time.perf_counter()
                try:
                    predictions = self._model.predict(
                        source=image,
                        imgsz=int(self._manifest.get("detector", {}).get("imgsz", 640))
                        if self._manifest
                        else 640,
                        conf=min(thresholds.values()),
                        device=self.device,
                        verbose=False,
                    )
                except Exception as exc:
                    raise ALPRInferenceError(f"Detector inference failed: {exc}") from exc

                detector_latency_ms = (time.perf_counter() - detector_started) * 1000
                prediction = predictions[0] if predictions else None

                plates, vehicles = self._extract_detections(prediction, thresholds)

                # Special Case: BICYCLE detected and no license plate found (BR-20)
                if not plates and vehicles:
                    top_vbox, top_vconf, top_vtype = vehicles[0]
                    if top_vtype == VehicleType.BICYCLE.value:
                        x1, y1, x2, y2 = clamp_bbox(
                            top_vbox.as_tuple, image.shape[1], image.shape[0]
                        )
                        clamped_vbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                        return ALPRResult(
                            plate_number=None,
                            raw_plate=None,
                            normalized_plate=None,
                            bbox=None,
                            confidence=top_vconf,
                            processing_time_ms=int((time.perf_counter() - started) * 1000),
                            requires_confirmation=requires_confirmation(
                                top_vconf, confirmation_thresh
                            ),
                            model_version=self.model_version,
                            detector_confidence=top_vconf,
                            combined_confidence=top_vconf,
                            provider="ultralytics-paddleocr",
                            detector_latency_ms=detector_latency_ms,
                            vehicle_type=VehicleType.BICYCLE.value,
                            vehicle_confidence=top_vconf,
                            bbox_vehicle=clamped_vbox,
                            building_id=building_id,
                        )

                # No plate found and not a bicycle
                if not plates:
                    top_vbox, top_vconf, top_vtype = (None, None, VehicleType.UNKNOWN.value)
                    if vehicles:
                        vbox_raw, top_vconf, top_vtype = vehicles[0]
                        vx1, vy1, vx2, vy2 = clamp_bbox(
                            vbox_raw.as_tuple, image.shape[1], image.shape[0]
                        )
                        top_vbox = BoundingBox(x1=vx1, y1=vy1, x2=vx2, y2=vy2)
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
                        vehicle_type=top_vtype,
                        vehicle_confidence=top_vconf,
                        bbox_vehicle=top_vbox,
                        building_id=building_id,
                    )

                # Plate found: associate with vehicle
                raw_bbox, detector_confidence = plates[0]
                assoc_vbox, assoc_vconf, vehicle_type = self._associate_plate_with_vehicle(
                    raw_bbox, vehicles
                )

                x1, y1, x2, y2 = clamp_bbox(raw_bbox.as_tuple, image.shape[1], image.shape[0])
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
                        vehicle_type=vehicle_type,
                        vehicle_confidence=assoc_vconf,
                        building_id=building_id,
                    )

                bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                clamped_vbox = None
                if assoc_vbox is not None:
                    vx1, vy1, vx2, vy2 = clamp_bbox(
                        assoc_vbox.as_tuple, image.shape[1], image.shape[0]
                    )
                    if vx2 > vx1 and vy2 > vy1:
                        clamped_vbox = BoundingBox(x1=vx1, y1=vy1, x2=vx2, y2=vy2)

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
                    vehicle_type=vehicle_type,
                    vehicle_confidence=assoc_vconf,
                    bbox_vehicle=clamped_vbox,
                    building_id=building_id,
                )

            confidence = min(detector_confidence, ocr_confidence)
            return ALPRResult(
                plate_number=plate,
                raw_plate=raw_plate,
                normalized_plate=plate,
                bbox=bbox,
                confidence=confidence,
                processing_time_ms=int((time.perf_counter() - started) * 1000),
                requires_confirmation=requires_confirmation(confidence, confirmation_thresh),
                model_version=self.model_version,
                detector_confidence=detector_confidence,
                ocr_confidence=ocr_confidence,
                combined_confidence=confidence,
                quality_flags=quality_flags,
                provider="ultralytics-paddleocr",
                detector_latency_ms=detector_latency_ms,
                ocr_latency_ms=ocr_latency_ms,
                vehicle_type=vehicle_type,
                vehicle_confidence=assoc_vconf,
                bbox_vehicle=clamped_vbox,
                building_id=building_id,
            )
        except (ALPRInvalidImageError, ALPRNotReadyError, ALPRProcessingError):
            raise
        except Exception as exc:
            raise ALPRProcessingError(f"Real ALPR inference failed: {exc}") from exc
