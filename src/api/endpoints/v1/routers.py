from fastapi import APIRouter

from src.api.endpoints.v1 import health
from src.config.logs_config import get_logger

logger = get_logger(__name__)

# Create v1 router
v1_router = APIRouter()

# Include always-available endpoints
v1_router.include_router(health.router, prefix="/health")

# --- Optional: metrics endpoint (requires observability extras) ---
try:
    from src.api.endpoints.v1 import metrics

    v1_router.include_router(
        metrics.router, prefix=""
    )  # metrics endpoint already has /metrics path
except ImportError:
    logger.info("Metrics endpoint not registered -- observability deps not installed")

# --- Optional: sample agent endpoints (require AI extras) ---
# The routers are always registered so the endpoint path exists;
# the DI chain returns 503 AGENT_UNAVAILABLE when AI deps are missing.
try:
    from src.api.endpoints.v1 import sample_agent, sample_di

    v1_router.include_router(sample_agent.router, prefix="/agent")
    v1_router.include_router(sample_di.router, prefix="/sample_di")
except ImportError:
    logger.info(
        "Sample agent endpoints not registered -- AI deps not installed"
    )