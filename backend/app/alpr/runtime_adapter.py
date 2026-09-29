"""Deterministic local demo runtime; never claims real recognition."""

from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
from app.alpr.interface import ALPRRuntime
from app.alpr.pt_provider import UltralyticsPaddleALPRRuntime
from app.alpr.schema import ALPRResult, BoundingBox
from app.alpr.utils import decode_image


class FakeALPRRuntime(ALPRRuntime):
    version = "mock-alpr-0.1.0"

    def __init__(self, scenario: str = "success"):
        self.scenario = scenario

    def is_ready(self) -> tuple[bool, str]:
        if self.scenario == "unavailable":
            return False, "DEMO: mock provider is intentionally unavailable."
        return True, "DEMO: deterministic mock provider; no real recognition."

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        if self.scenario == "unavailable":
            raise ALPRNotReadyError(self.is_ready()[1])
        if self.scenario == "processing-error":
            raise ALPRProcessingError("DEMO: mock processing error.")
        height, width = decode_image(image_bytes).shape[:2]
        if self.scenario == "no-plate":
            return ALPRResult(
                plate_number=None,
                bbox=None,
                confidence=0.0,
                processing_time_ms=0,
                requires_confirmation=True,
                model_version=self.version,
            )
        confidence = 0.5 if self.scenario == "low-confidence" else 0.98
        return ALPRResult(
            plate_number="29A-123.45",
            bbox=BoundingBox(x1=0, y1=0, x2=width, y2=height),
            confidence=confidence,
            processing_time_ms=0,
            requires_confirmation=confidence < 0.85,
            model_version=self.version,
        )


class UnavailableRuntime(ALPRRuntime):
    version = "not-configured"

    def is_ready(self) -> tuple[bool, str]:
        return False, "Provider is not wired. Configure mock for the local demo."

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        raise ALPRNotReadyError(self.is_ready()[1])


# Backward-compatible name used by the existing integration fixtures.
ai_runtime = FakeALPRRuntime()


def create_runtime(
    provider: str,
    *,
    manifest_path: str = "models/alpr-manifest.json",
    device: str = "cpu",
    detector_confidence: float = 0.25,
    confirmation_threshold: float = 0.85,
    ocr_margin: float = 0.08,
    ocr_enabled: bool = False,
    mock_scenario: str = "success",
) -> ALPRRuntime:
    if provider == "mock":
        return FakeALPRRuntime(mock_scenario)
    if provider == "real":
        return UltralyticsPaddleALPRRuntime(
            manifest_path,
            device=device,
            detector_confidence=detector_confidence,
            confirmation_threshold=confirmation_threshold,
            ocr_margin=ocr_margin,
            ocr_enabled=ocr_enabled,
        )
    return UnavailableRuntime()
