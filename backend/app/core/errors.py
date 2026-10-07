import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

logger = logging.getLogger("visionpark.errors")


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", None) or str(uuid4())


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    correlation_id = _correlation_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or {},
            "correlation_id": correlation_id,
        },
        headers={**(headers or {}), "X-Correlation-ID": correlation_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    def record_failure(request: Request, code: str, status: int) -> None:
        # Health probes and preview frames must not flood durable event storage.
        if request.url.path.endswith("/health/ready") or request.url.path.endswith("/health/live"):
            return
        if request.url.path.endswith("/alpr/detections"):
            return
        from app.database.session import database
        from app.modules.operations.models import ErrorEvent, Notification

        try:
            with database.create_session() as session:
                actor = getattr(request.state, "actor_id", None)
                event = ErrorEvent(
                    user_id=actor,
                    code=code,
                    status=status,
                    source="backend",
                    correlation_id=_correlation_id(request)[:64],
                    message=f"Request failed ({code}).",
                )
                session.add(event)
                if actor:
                    session.add(
                        Notification(
                            user_id=actor,
                            title="Operation failed",
                            message=f"Request failed ({code}).",
                            event_key=f"backend-{event.id or uuid4()}",
                        )
                    )
                session.commit()
        except Exception:
            # Failure reporting cannot replace the original response or recurse when DB is down.
            logger.warning("Could not persist backend error event")

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            record_failure(request, exc.code, exc.status_code)
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in exc.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request data is invalid.",
            details={"errors": errors},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        default_codes = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            503: "DEPENDENCY_UNAVAILABLE",
        }
        code = default_codes.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail)
        details: dict[str, Any] = {}
        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code", code))
            message = str(exc.detail.get("message", "Request failed."))
            details = dict(exc.detail.get("details", {}))
        return _error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
            headers=exc.headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        record_failure(request, "DATABASE_UNAVAILABLE", 503)
        logger.exception(
            "Database request failed",
            exc_info=exc,
            extra={"correlation_id": _correlation_id(request)},
        )
        return _error_response(
            request,
            status_code=503,
            code="DATABASE_UNAVAILABLE",
            message="Database is unavailable.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        record_failure(request, "INTERNAL_SERVER_ERROR", 500)
        logger.exception(
            "Unexpected request failure",
            exc_info=exc,
            extra={"correlation_id": _correlation_id(request)},
        )
        return _error_response(
            request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
        )
