from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.health import router as health_router
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.core.readiness import UnconfiguredALPRProbe
from app.database.seed import seed_database
from app.database.session import database


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.debug)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.configure(app_settings.database_url)
        if app_settings.auto_seed:
            session = database.create_session()
            try:
                seed_database(session, app_settings)
            finally:
                session.close()
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
    )
    app.dependency_overrides[get_settings] = lambda: app_settings
    app.state.settings = app_settings
    app.state.alpr_readiness_probe = UnconfiguredALPRProbe(app_settings.alpr_provider)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()
