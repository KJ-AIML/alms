from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from src.api.middlewares.error_handler import ErrorHandlerMiddleware
from src.api.middlewares.logging import LoggingMiddleware
from src.api.middlewares.observability import ObservabilityMiddleware
from src.api.middlewares.security import APIKeyMiddleware
from src.api.router.routers import api_router
from src.config.logs_config import get_logger
from src.config.settings import settings
from src.observability import setup_tracing, setup_metrics, instrument_fastapi

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")

    # Fail fast on unsafe production defaults before anything else starts
    settings.validate_production_settings()

    # Initialize observability
    setup_metrics(
        service_name=settings.SERVICE_NAME,
        service_version=settings.APP_VERSION,
    )

    # Setup tracing (OTLP endpoint from env or console in debug)
    otlp_endpoint = getattr(settings, "OTLP_ENDPOINT", None)
    setup_tracing(
        service_name=settings.SERVICE_NAME,
        service_version=settings.APP_VERSION,
        otlp_endpoint=otlp_endpoint,
        console_export=settings.DEBUG,
    )

    # Instrument FastAPI app for tracing
    instrument_fastapi(app)

    logger.info("Observability initialized - Tracing and Metrics ready")
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
        docs_url=None,  # Disable default Swagger UI
        redoc_url=None,  # Disable ReDoc
        openapi_url="/openapi.json",  # Keep OpenAPI JSON endpoint
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
    app.add_middleware(ObservabilityMiddleware)
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
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
        )

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
