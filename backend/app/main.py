import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging

request_logger = logging.getLogger("app.request")


def _error(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body}, headers=headers)


def create_app() -> FastAPI:
    settings = get_settings()  # raises on invalid configuration -> fails fast at startup
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logging.getLogger(__name__).info(
            "Starting %s v%s (env=%s)", settings.app_name, __version__, settings.app_env
        )
        yield

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Intelligent IT Incident Prediction, Log Anomaly Detection, "
            "Investigation and Root Cause Analysis Platform"
        ),
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next: Any) -> Any:
        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        request_logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only field location + message are returned; submitted values (passwords) are never echoed.
        details = [
            {"field": ".".join(str(p) for p in err["loc"]), "message": str(err["msg"])}
            for err in exc.errors()
        ]
        return _error(422, "validation_error", "Request validation failed", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(
            exc.status_code, "http_error", str(exc.detail), headers=dict(exc.headers or {})
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        request_logger.error("Unhandled exception", exc_info=exc)
        return _error(500, "internal_error", "An unexpected error occurred")

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
