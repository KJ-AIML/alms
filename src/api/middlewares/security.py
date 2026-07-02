import secrets

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.endpoints.v1.schemas.base import AppResponse, ErrorDetail
from src.config.settings import settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check for a valid API key in headers.
    Only active if X_API_KEY is configured in settings.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip security checks in debug mode for convenience,
        # or if no key is configured.
        api_key = getattr(settings, "X_API_KEY", None)
        public_paths = {
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        if settings.DEBUG or not api_key:
            return await call_next(request)

        # Skip for health checks and documentation
        if request.url.path in public_paths or request.url.path.startswith(
            f"{settings.API_PREFIX}/v1/health"
        ):
            return await call_next(request)

        header_key = request.headers.get("X-API-KEY")
        if not header_key or not secrets.compare_digest(header_key, api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=AppResponse(
                    success=False,
                    error=ErrorDetail(
                        code="UNAUTHORIZED", message="Invalid or missing API Key"
                    ),
                    request_id=getattr(request.state, "request_id", "unknown"),
                ).model_dump(),
            )

        return await call_next(request)
