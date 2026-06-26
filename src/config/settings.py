import logging
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Application identity
    APP_NAME: str = "ALMS"
    APP_DESCRIPTION: str = "Backend API for ALMS"
    APP_VERSION: str = "0.3.0"
    SERVICE_NAME: str = "alms"

    # Feature flags — set to False to disable optional dependencies
    AI_ENABLED: bool = False
    DATABASE_ENABLED: bool = True
    REDIS_ENABLED: bool = False

    # AI provider settings
    MODEL_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_BASIC: str | None = None
    OPENAI_MODEL_REASONING: str | None = None

    # Google settings
    GOOGLE_API_KEY: str | None = None
    GOOGLE_MODEL_BASIC: str | None = None
    GOOGLE_MODEL_REASONING: str | None = None

    # Environment settings
    DEBUG: bool = False
    SECRET_KEY: str = "your-default-secret-key"

    # Database settings
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_URL: str | None = None

    # API settings
    API_PREFIX: str = "/api"

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    # Cache settings
    CACHE_TTL: int = 900

    # Logging settings
    LOG_LEVEL: str = "info"
    LOG_SAVE_TO_FILE: bool = False
    LOG_FILE: str = "src/logs/app.log"
    LOG_AUTO_SETUP: bool = True
    LOG_MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # Server Configuration
    SERVER_PORT: int = 3000
    SERVER_HOST: str = "0.0.0.0"

    # Allowed hosts
    ALLOWED_HOSTS: List[str] = ["*"]

    # Security settings
    X_API_KEY: str | None = None

    # Observability settings
    OTLP_ENDPOINT: str | None = None  # e.g., "http://localhost:4317" for Jaeger/Tempo
    METRICS_ENABLED: bool = True
    TRACING_ENABLED: bool = True

    @property
    def is_production(self) -> bool:
        return not self.DEBUG

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    def validate_production_settings(self) -> None:
        """Raise ValueError if unsafe defaults are present in production mode."""
        if self.DEBUG:
            return
        errors = []
        if self.SECRET_KEY == "your-default-secret-key":
            errors.append(
                "SECRET_KEY must not be the default placeholder in production"
            )
        if "*" in self.ALLOWED_HOSTS:
            errors.append("ALLOWED_HOSTS must not contain '*' in production")
        if (
            self.AI_ENABLED
            and self.MODEL_PROVIDER == "openai"
            and not self.OPENAI_API_KEY
        ):
            errors.append(
                "OPENAI_API_KEY is required when AI_ENABLED=True and MODEL_PROVIDER=openai"
            )
        if errors:
            raise ValueError(
                "Production configuration errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    class Config:
        env_file = BASE_DIR / ".env"
        case_sensitive = True


settings = Settings()

# Post-initialization: warn if AI is enabled without a key in production
if not settings.DEBUG and settings.AI_ENABLED and not settings.OPENAI_API_KEY:
    logger = logging.getLogger(__name__)
    logger.warning("AI_ENABLED=True but OPENAI_API_KEY is not set in production mode!")
