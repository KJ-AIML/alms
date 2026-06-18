"""Database connection and session management.

SQLAlchemy imports are wrapped so the module can be imported even when
SQLAlchemy is not installed (core-api profile). The engine and session
factory are created lazily on first access.
"""

from __future__ import annotations

from src.config.logs_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# Lazily-resolved globals
_engine = None
_AsyncSessionLocal = None
_Base = None
_sqlalchemy_available: bool | None = None


def _ensure_sqlalchemy() -> bool:
    """Import SQLAlchemy once and cache the result.  Returns True on success."""
    global _sqlalchemy_available, _engine, _AsyncSessionLocal, _Base
    if _sqlalchemy_available is not None:
        return _sqlalchemy_available
    try:
        from sqlalchemy import text  # noqa: F401
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.orm import DeclarativeBase

        _engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
        )

        _AsyncSessionLocal = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        class _Base(DeclarativeBase):
            pass

        _sqlalchemy_available = True
        logger.info("SQLAlchemy engine and session factory initialised")
    except ImportError:
        _sqlalchemy_available = False
        logger.info("SQLAlchemy not installed -- database features unavailable")
    return _sqlalchemy_available


def Base():
    """Return the declarative base class."""
    if not _ensure_sqlalchemy():
        raise RuntimeError("SQLAlchemy is not installed. Install with: uv sync --extra db")
    return _Base


async def check_database_connection() -> bool:
    """Run a lightweight readiness check against the configured database."""
    if not settings.DATABASE_ENABLED:
        return True
    if not _ensure_sqlalchemy():
        return False
    try:
        from sqlalchemy import text

        async with _AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db():
    """Dependency for getting async database sessions"""
    if not _ensure_sqlalchemy():
        raise RuntimeError("SQLAlchemy is not installed. Install with: uv sync --extra db")
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()