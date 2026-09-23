from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.readiness import (
    ALPRReadinessProbe,
    ReadinessStatus,
    get_alpr_readiness_probe,
)
from app.database.session import get_database_readiness

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {"status": "alive", "version": settings.app_version}


@router.get("/health/ready")
def readiness(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    database_status: Annotated[ReadinessStatus, Depends(get_database_readiness)],
    alpr_probe: Annotated[ALPRReadinessProbe, Depends(get_alpr_readiness_probe)],
) -> JSONResponse:
    alpr_status = alpr_probe.readiness()
    is_ready = database_status.ready and alpr_status.ready
    body: dict[str, Any] = {
        "status": "ready" if is_ready else "not_ready",
        "version": settings.app_version,
        "database": database_status.to_dict(),
        "alpr": alpr_status.to_dict(),
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
    return JSONResponse(status_code=200 if is_ready else 503, content=body)
