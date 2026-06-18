from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middlewares.error_handler import ErrorHandlerMiddleware
from src.api.middlewares.logging import LoggingMiddleware
from src.api.middlewares.security import APIKeyMiddleware
from src.api.router.routers import api_router
from src.config.logs_config import get_logger
from src.config.settings import settings

# --- Optional imports: Scalar API docs ---
try:
    from scalar_fastapi import get_scalar_api_reference

    _scalar_available = True
except ImportError:  # pragma: no cover -- scalar is an optional dependency
    _scalar_available = False
    get_scalar_api_reference = None  # type: ignore[assignment]

# --- Optional imports: Observability (OpenTelemetry + Prometheus) ---
try:
    from src.observability import setup_tracing, setup_metrics, instrument_fastapi

    _observability_available = True
except ImportError:  # pragma: no cover -- observability deps are optional
    _observability_available = False

# --- Optional: ObservabilityMiddleware (resolved inside create_app) ---
_ObservabilityMiddleware = None

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")

    # Fail fast on unsafe production defaults before anything else starts
    settings.validate_production_settings()

    # Initialize observability only when dependencies are available and enabled
    if _observability_available:
        if settings.METRICS_ENABLED:
            setup_metrics(
                service_name=settings.SERVICE_NAME,
                service_version=settings.APP_VERSION,
            )

        if settings.TRACING_ENABLED:
            otlp_endpoint = getattr(settings, "OTLP_ENDPOINT", None)
            setup_tracing(
                service_name=settings.SERVICE_NAME,
                service_version=settings.APP_VERSION,
                otlp_endpoint=otlp_endpoint,
                console_export=settings.DEBUG,
            )
            instrument_fastapi(app)

        logger.info("Observability initialized - Tracing and Metrics ready")
    else:
        logger.info(
            "Observability not available -- skipping tracing and metrics setup"
        )

    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # Register Middlewares (order matters - last added is first executed)
    # ObservabilityMiddleware is resolved lazily here so optional deps
    # do not block core-api startup.
    global _ObservabilityMiddleware
    try:
        from src.api.middlewares.observability import ObservabilityMiddleware

        _ObservabilityMiddleware = ObservabilityMiddleware
    except ImportError:
        pass

    if _ObservabilityMiddleware is not None:
        app.add_middleware(_ObservabilityMiddleware)
    elif not settings.METRICS_ENABLED and not settings.TRACING_ENABLED:
        logger.info(
            "ObservabilityMiddleware skipped -- metrics and tracing are disabled"
        )
    else:
        logger.warning(
            "ObservabilityMiddleware unavailable -- observability dependencies may be missing"
        )

    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Health check endpoint
    @app.get("/")
    async def check():
        return {
            "status": "alive",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    # Scalar API Documentation
    @app.get("/docs", include_in_schema=False)
    async def scalar_html():
        if _scalar_available:
            return get_scalar_api_reference(
                openapi_url=app.openapi_url,
                title=app.title,
            )
        return {
            "detail": "Scalar docs not installed. Install with: uv sync --extra docs"
        }

    logger.info("FastAPI application configured successfully")
    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.LOG_LEVEL,
        reload=settings.DEBUG,
        access_log=False,
    )