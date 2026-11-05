"""VisionPark AI & ALPR Module."""

from .fire_provider import FireSmokeDetectorRuntime
from .interface import ALPRRuntime
from .multi_frame_voter import MultiFrameVoter, VoteResult
from .pt_provider import UltralyticsPaddleALPRRuntime
from .schema import ALPRHTTPResponse, ALPRResult, BoundingBox, FireSignalEvent, VehicleType
from .service import ALPRApplicationService

__all__ = [
    "ALPRApplicationService",
    "ALPRHTTPResponse",
    "ALPRResult",
    "ALPRRuntime",
    "BoundingBox",
    "FireSignalEvent",
    "FireSmokeDetectorRuntime",
    "MultiFrameVoter",
    "UltralyticsPaddleALPRRuntime",
    "VehicleType",
    "VoteResult",
]
