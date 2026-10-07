"""Factory for the real recognition runtime. Test doubles live in tests only."""

from app.alpr.interface import ALPRRuntime
from app.alpr.pt_provider import UltralyticsPaddleALPRRuntime


def create_runtime(
    provider: str,
    *,
    manifest_path: str = "models/alpr-manifest.json",
    device: str = "cpu",
    detector_confidence: float = 0.25,
    confirmation_threshold: float = 0.85,
    ocr_margin: float = 0.08,
    ocr_enabled: bool = False,
) -> ALPRRuntime:
    if provider == "real":
        return UltralyticsPaddleALPRRuntime(
            manifest_path,
            device=device,
            detector_confidence=detector_confidence,
            confirmation_threshold=confirmation_threshold,
            ocr_margin=ocr_margin,
            ocr_enabled=ocr_enabled,
        )
    raise ValueError("ALPR_PROVIDER must be real; mock recognition is no longer supported")
