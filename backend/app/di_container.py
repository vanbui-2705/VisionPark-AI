from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.alpr.service import ALPRApplicationService
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.integrations.persistence.detection_recorder_impl import DatabaseDetectionRecorder
from app.integrations.persistence.lane_checker_impl import DatabaseLaneChecker
from app.integrations.storage.local_storage import LocalStorageAdapter


def get_alpr_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ALPRApplicationService:
    return ALPRApplicationService(
        runtime=request.app.state.alpr_runtime,
        lane_checker=DatabaseLaneChecker(session),
        image_storage=LocalStorageAdapter(settings),
        detection_recorder=DatabaseDetectionRecorder(session),
    )
