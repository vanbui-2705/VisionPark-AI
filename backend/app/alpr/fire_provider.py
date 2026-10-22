"""Fire and Smoke detection runtime with multi-layer false alarm filter (SPEC-AI-03)."""

from __future__ import annotations

import collections
import datetime
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
    ALPRManifestError,
    ALPRModelLoadError,
    ALPRModelMissingError,
    ALPRNotReadyError,
)
from .schema import FireSignalEvent
from .utils import clamp_bbox, decode_image

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class DetectionHistoryItem:
    def __init__(
        self, timestamp: float, bbox: tuple[int, int, int, int], confidence: float, area: int
    ):
        self.timestamp = timestamp
        self.bbox = bbox
        self.confidence = confidence
        self.area = area


class FireSmokeDetectorRuntime:
    """Runtime running ``fire.onnx`` to detect flame and smoke with 5-layer filter."""

    def __init__(
        self,
        manifest_path: str = "models/fire-manifest.json",
        *,
        device: str = "cpu",
        fire_confidence: float = 0.45,
        smoke_confidence: float = 0.40,
        temporal_debounce_frames: int = 5,
        temporal_window_seconds: float = 3.0,
        smoke_persistence_seconds: float = 2.5,
    ) -> None:
        self.manifest_path = self._resolve_path(manifest_path)
        self.device = device
        self.fire_confidence = fire_confidence
        self.smoke_confidence = smoke_confidence
        self.temporal_debounce_frames = temporal_debounce_frames
        self.temporal_window_seconds = temporal_window_seconds
        self.smoke_persistence_seconds = smoke_persistence_seconds

        self.version = "fire-smoke-unloaded"
        self._manifest: dict[str, Any] | None = None
        self._model: Any = None
        self._load_error: ALPRNotReadyError | None = None
        self._inference_lock = threading.Lock()

        # Rolling history per (camera_id, event_type) -> deque of DetectionHistoryItem
        self._history: dict[tuple[str, str], collections.deque[DetectionHistoryItem]] = (
            collections.defaultdict(lambda: collections.deque(maxlen=30))
        )

        try:
            self._manifest = self._read_manifest()
            self.version = str(self._manifest.get("model_version", self.version))
            rules = self._manifest.get("rules", {})
            self.temporal_debounce_frames = int(
                rules.get("temporal_debounce_frames", self.temporal_debounce_frames)
            )
            self.temporal_window_seconds = float(
                rules.get("temporal_window_seconds", self.temporal_window_seconds)
            )
            self.smoke_persistence_seconds = float(
                rules.get("smoke_persistence_seconds", self.smoke_persistence_seconds)
            )
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
            raise ALPRModelMissingError(f"Fire model manifest not found: {self.manifest_path}")
        try:
            with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ALPRManifestError(f"Could not read fire manifest: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ALPRManifestError("Fire model manifest must be a JSON object")
        if not manifest.get("model_version"):
            raise ALPRManifestError("Fire model manifest is missing model_version")
        return manifest

    def _resolve_weights_path(self, manifest: dict[str, Any]) -> Path:
        detector = manifest.get("detector", {})
        raw_path = detector.get("weights_path") or manifest.get("weights_path")
        if not raw_path:
            raise ALPRManifestError("Fire manifest missing detector weights_path")
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
            raise ALPRModelMissingError(f"Fire weights not found: {weights_path}")

        expected_hash = manifest.get("detector", {}).get("sha256") or manifest.get("sha256")
        if expected_hash:
            digest = hashlib.sha256(weights_path.read_bytes()).hexdigest().upper()
            if digest != str(expected_hash).upper():
                raise ALPRChecksumMismatchError("Fire weights checksum mismatch")
        return manifest, weights_path

    def _ensure_loaded(self) -> None:
        if self._model is not None:
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
            raise ALPRDependencyError("Ultralytics dependency missing.") from exc

        try:
            try:
                self._model = YOLO(str(weights_path), task="detect")
            except TypeError:
                self._model = YOLO(str(weights_path))
            self.version = str(manifest["model_version"])
        except Exception as exc:
            self._model = None
            raise ALPRModelLoadError(f"Could not load fire detector: {exc}") from exc

    def is_ready(self) -> tuple[bool, str]:
        try:
            self._ensure_loaded()
        except ALPRNotReadyError as exc:
            return False, str(exc)
        return True, f"Loaded fire/smoke detector {self.model_version}"

    @staticmethod
    def _scalar(value: Any) -> float:
        if hasattr(value, "item"):
            return float(value.item())
        if isinstance(value, (list, tuple)):
            return float(value[0])
        return float(value)

    @staticmethod
    def _is_in_exclusion_zone(
        bbox: tuple[int, int, int, int], exclusion_masks: list[tuple[int, int, int, int]]
    ) -> bool:
        """Layer 3: Check if bounding box significantly overlaps with static exclusion mask."""
        if not exclusion_masks:
            return False
        bx1, by1, bx2, by2 = bbox
        b_area = max(1, (bx2 - bx1) * (by2 - by1))

        for ex1, ey1, ex2, ey2 in exclusion_masks:
            ix1, iy1 = max(bx1, ex1), max(by1, ey1)
            ix2, iy2 = min(bx2, ex2), min(by2, ey2)
            if ix2 > ix1 and iy2 > iy1:
                inter_area = (ix2 - ix1) * (iy2 - iy1)
                if inter_area / b_area >= 0.50:
                    return True
        return False

    def reset_camera(self, camera_id: str) -> None:
        """Reset temporal history for a specific camera."""
        for event_type in ("FIRE", "SMOKE"):
            self._history.pop((camera_id, event_type), None)

    def process_frame(
        self,
        frame_or_bytes: Any,
        camera_id: str,
        *,
        building_id: str | None = None,
        zone_code: str | None = None,
        settings: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> list[FireSignalEvent]:
        """
        Process a surveillance camera frame through 5-layer false alarm filter.
        Returns a list of FireSignalEvent instances for verified flame or smoke.
        """
        self._ensure_loaded()
        now = timestamp if timestamp is not None else time.time()

        if isinstance(frame_or_bytes, bytes):
            image = decode_image(frame_or_bytes)
        else:
            image = frame_or_bytes

        settings = settings or {}
        fire_threshold = float(settings.get("fire_confidence", self.fire_confidence))
        smoke_threshold = float(settings.get("smoke_confidence", self.smoke_confidence))
        min_frames = int(settings.get("temporal_debounce_frames", self.temporal_debounce_frames))
        window_sec = float(settings.get("temporal_window_seconds", self.temporal_window_seconds))
        smoke_persist_sec = float(
            settings.get("smoke_persistence_seconds", self.smoke_persistence_seconds)
        )
        exclusion_masks = settings.get("exclusion_masks", [])

        img_h, img_w = image.shape[:2]

        with self._inference_lock:
            try:
                predictions = self._model.predict(
                    source=image,
                    imgsz=640,
                    conf=min(fire_threshold, smoke_threshold),
                    device=self.device,
                    verbose=False,
                )
            except Exception as exc:
                raise ALPRInferenceError(f"Fire detector inference failed: {exc}") from exc

        prediction = predictions[0] if predictions else None
        boxes = getattr(prediction, "boxes", None)
        names = getattr(self._model, "names", {})

        raw_candidates: list[tuple[str, float, tuple[int, int, int, int]]] = []
        if boxes is not None and len(boxes) > 0:
            for i in range(len(boxes)):
                cls_id = int(self._scalar(boxes.cls[i]))
                label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                label_fold = str(label).casefold()

                conf = self._scalar(boxes.conf[i])
                raw_coords = boxes.xyxy[i]
                coords = raw_coords.tolist() if hasattr(raw_coords, "tolist") else list(raw_coords)

                event_type = None
                if "fire" in label_fold or "flame" in label_fold:
                    if conf >= fire_threshold:  # Layer 1: Confidence
                        event_type = "FIRE"
                elif "smoke" in label_fold:
                    if conf >= smoke_threshold:  # Layer 1: Confidence
                        event_type = "SMOKE"

                if event_type:
                    cx1, cy1, cx2, cy2 = clamp_bbox(
                        (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])),
                        img_w,
                        img_h,
                    )
                    if cx2 > cx1 and cy2 > cy1:
                        # Layer 3: Static exclusion zone check
                        if not self._is_in_exclusion_zone((cx1, cy1, cx2, cy2), exclusion_masks):
                            raw_candidates.append((event_type, conf, (cx1, cy1, cx2, cy2)))

        events: list[FireSignalEvent] = []

        # Process each detected class
        for event_type in ("FIRE", "SMOKE"):
            matching = [c for c in raw_candidates if c[0] == event_type]
            history = self._history[(camera_id, event_type)]

            if matching:
                # Pick detection with highest confidence in current frame
                best_match = max(matching, key=lambda c: c[1])
                _, conf, bbox = best_match
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                history.append(DetectionHistoryItem(now, bbox, conf, area))

            # Prune old history outside temporal window
            while history and (now - history[0].timestamp > window_sec):
                history.popleft()

            # Layer 2: Temporal debounce check (minimum frames in window)
            if len(history) >= min_frames:
                # Layer 4: Smoke persistence & expansion check
                if event_type == "SMOKE":
                    oldest = history[0]
                    duration = now - oldest.timestamp
                    expanding = history[-1].area >= (oldest.area * 0.85)
                    if duration < smoke_persist_sec and not expanding:
                        continue  # Dissipating quickly (e.g. exhaust puff), skip

                # Layer 5: Consensus & Verification status
                confirmed_count = len(history)
                latest = history[-1]
                status = (
                    "CONFIRMED"
                    if (confirmed_count >= 10 or latest.confidence >= 0.80)
                    else "VERIFYING"
                )

                events.append(
                    FireSignalEvent(
                        building_id=building_id,
                        camera_id=camera_id,
                        zone_code=zone_code,
                        event_type=event_type,
                        confidence=round(latest.confidence, 4),
                        confirmed_frame_count=confirmed_count,
                        bbox=list(latest.bbox),
                        timestamp=datetime.datetime.now(datetime.UTC),
                        status=status,
                    )
                )

        return events
