from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from resume_ops_api.api.models import ErrorResponse
from resume_ops_api.api.routes import router
from resume_ops_api.core.config import Settings, get_settings
from resume_ops_api.core.exceptions import AppError
from resume_ops_api.core.logging import configure_logging
from resume_ops_api.services.container import ServiceContainer, build_container


def create_app(
    settings: Settings | None = None,
    **overrides: Any,
) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    container = build_container(app_settings, **overrides)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        app.state.ready = False
        await container.start()
        app.state.ready = True
        try:
            yield
        finally:
            app.state.ready = False
            await container.stop()

    app = FastAPI(
        title="Resume Ops API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                details=exc.details or None,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code="request_validation_failed",
                message="The request body is invalid.",
                details={"errors": exc.errors()},
            ).model_dump(mode="json"),
        )

    return app

