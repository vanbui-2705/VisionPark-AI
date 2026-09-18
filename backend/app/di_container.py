from app.alpr.service import ALPRApplicationService
from app.alpr.runtime_adapter import ai_runtime
from app.integrations.storage import get_storage_adapter
from app.alpr.ports.lane_checker import ActiveLaneChecker
from app.alpr.ports.detection_recorder import DetectionRecorder
from app.alpr.ports.lane_checker_impl import DatabaseLaneChecker
from app.alpr.ports.detection_recorder_impl import DatabaseDetectionRecorder


def get_alpr_service() -> ALPRApplicationService:
    """Factory để tạo ALPR service với đầy đủ dependencies."""
    return ALPRApplicationService(
        runtime=ai_runtime,
        lane_checker=DatabaseLaneChecker(),
        image_storage=get_storage_adapter(),
        detection_recorder=DatabaseDetectionRecorder()
    )