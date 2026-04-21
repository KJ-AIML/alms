from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.api.endpoints.v1.schemas.base import AppResponse
from src.config.logs_config import get_logger
from src.config.settings import settings
from src.database.connection import check_database_connection

router = APIRouter()
logger = get_logger(__name__)


def _health_payload(status_text: str, ready: bool, dependencies: dict | None = None) -> dict:
    return {
        "status": status_text,
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
        "ready": ready,
        "dependencies": dependencies or {},
    }


@router.get("/live", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)
async def live_check():
    """Liveness probe that does not depend on downstream providers."""
    logger.debug("Liveness probe requested")
    return AppResponse(success=True, data=_health_payload("alive", ready=True))


@router.get("/ready", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)
async def ready_check():
    """Readiness probe that verifies critical dependencies."""
    logger.debug("Readiness probe requested")

    db_ready = await check_database_connection()
    payload = _health_payload(
        status_text="ready" if db_ready else "degraded",
        ready=db_ready,
        dependencies={"database": "healthy" if db_ready else "unhealthy"},
    )

    if db_ready:
        return AppResponse(success=True, data=payload)

    logger.error("Database readiness check failed")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=AppResponse(success=False, data=payload).model_dump(),
    )


@router.get("", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)
async def health_check():
    """Backward-compatible alias for the readiness probe."""
    return await ready_check()
