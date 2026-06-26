from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.observability import DatabaseMetricsMiddleware
from src.database.repositories.base import BaseRepository
from src.observability.tracing import trace_span

T = TypeVar("T")


class SQLAlchemyRepository(BaseRepository[T], Generic[T]):
    """
    SQLAlchemy async repository implementation for CRUD operations.
    Includes automatic metrics collection and distributed tracing.

    Usage:
        class UserRepository(SQLAlchemyRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """

    def __init__(self, model: Type[T], session: AsyncSession):
        super().__init__(model)
        self.session = session
        self._table_name = getattr(model, "__tablename__", model.__name__.lower())

    async def get(self, id: Any) -> Optional[T]:
        """Get a single record by ID."""
        with trace_span(
            f"db.get.{self._table_name}",
            {"table": self._table_name, "operation": "get", "id": str(id)},
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("get", self._table_name, duration)
            return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination."""
        with trace_span(
            f"db.get_all.{self._table_name}",
            {
                "table": self._table_name,
                "operation": "get_all",
                "skip": skip,
                "limit": limit,
            },
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                select(self.model).offset(skip).limit(limit)
            )
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query(
                "get_all", self._table_name, duration
            )
            return result.scalars().all()

    async def create(self, obj_in: T) -> T:
        """Create a new record."""
        with trace_span(
            f"db.create.{self._table_name}",
            {"table": self._table_name, "operation": "create"},
        ):
            start_time = __import__("time").time()
            self.session.add(obj_in)
            await self.session.flush()
            await self.session.refresh(obj_in)
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("create", self._table_name, duration)
            return obj_in

    async def update(self, id: Any, obj_in: dict) -> Optional[T]:
        """Update a record by ID."""
        with trace_span(
            f"db.update.{self._table_name}",
            {"table": self._table_name, "operation": "update", "id": str(id)},
        ):
            start_time = __import__("time").time()
            await self.session.execute(
                update(self.model).where(self.model.id == id).values(**obj_in)
            )
            await self.session.flush()
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("update", self._table_name, duration)
            return await self.get(id)

    async def delete(self, id: Any) -> bool:
        """Delete a record by ID."""
        with trace_span(
            f"db.delete.{self._table_name}",
            {"table": self._table_name, "operation": "delete", "id": str(id)},
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.flush()
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("delete", self._table_name, duration)
            return result.rowcount > 0

    async def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Get a single record by a specific field."""
        with trace_span(
            f"db.get_by_field.{self._table_name}",
            {
                "table": self._table_name,
                "operation": "get_by_field",
                "field": field_name,
            },
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                select(self.model).where(getattr(self.model, field_name) == value)
            )
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query(
                "get_by_field", self._table_name, duration
            )
            return result.scalar_one_or_none()

    async def get_many_by_field(
        self, field_name: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[T]:
        """Get multiple records by a specific field with pagination."""
        with trace_span(
            f"db.get_many_by_field.{self._table_name}",
            {
                "table": self._table_name,
                "operation": "get_many_by_field",
                "field": field_name,
            },
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                select(self.model)
                .where(getattr(self.model, field_name) == value)
                .offset(skip)
                .limit(limit)
            )
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query(
                "get_many_by_field", self._table_name, duration
            )
            return result.scalars().all()

    async def exists(self, id: Any) -> bool:
        """Check if a record exists by ID."""
        with trace_span(
            f"db.exists.{self._table_name}",
            {"table": self._table_name, "operation": "exists", "id": str(id)},
        ):
            start_time = __import__("time").time()
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            exists = result.scalar_one_or_none() is not None
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("exists", self._table_name, duration)
            return exists

    async def count(self) -> int:
        """Count total records."""
        with trace_span(
            f"db.count.{self._table_name}",
            {"table": self._table_name, "operation": "count"},
        ):
            start_time = __import__("time").time()
            from sqlalchemy import func
            result = await self.session.execute(
                select(func.count()).select_from(self.model)
            )
            count = result.scalar()
            duration = __import__("time").time() - start_time
            DatabaseMetricsMiddleware.record_query("count", self._table_name, duration)
            return count
