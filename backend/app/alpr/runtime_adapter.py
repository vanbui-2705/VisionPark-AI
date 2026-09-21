"""Deterministic local demo runtime; never claims real recognition."""

from app.alpr.errors import ALPRNotReadyError
from app.alpr.interface import ALPRRuntime
from app.alpr.schema import ALPRResult, BoundingBox
from app.alpr.utils import decode_image


class FakeALPRRuntime(ALPRRuntime):
    version = "mock-alpr-0.1.0"

    def is_ready(self) -> tuple[bool, str]:
        return True, "DEMO: deterministic mock provider; no real recognition."

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        height, width = decode_image(image_bytes).shape[:2]
        return ALPRResult(
            plate_number="29A-123.45",
            bbox=BoundingBox(x1=0, y1=0, x2=width, y2=height),
            confidence=0.98,
            processing_time_ms=0,
            requires_confirmation=False,
        )


class UnavailableRuntime(ALPRRuntime):
    version = "not-configured"

    def is_ready(self) -> tuple[bool, str]:
        return False, "Provider is not wired. Configure mock for the local demo."

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        raise ALPRNotReadyError(self.is_ready()[1])


def create_runtime(provider: str) -> ALPRRuntime:
    # ONNX output decoding is still a placeholder owned by the AI team.
    return FakeALPRRuntime() if provider == "mock" else UnavailableRuntime()
