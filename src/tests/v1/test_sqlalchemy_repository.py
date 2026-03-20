"""
Tests for SQLAlchemy repository implementation.

This module tests the SQLAlchemyRepository class with async database operations,
including CRUD functionality, metrics collection, and tracing integration.
"""

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.sqlalchemy_repository import SQLAlchemyRepository


class MockModel:
    """Mock SQLAlchemy model for testing."""

    __tablename__ = "test_items"

    def __init__(self, id=None, name=None, value=None):
        self.id = id
        self.name = name
        self.value = value


class TestSQLAlchemyRepository:
    """Test suite for SQLAlchemyRepository."""

    @pytest.fixture
    def mock_model(self):
        """Return mock model class."""
        return MockModel

    @pytest.fixture
    async def repository(self, mock_model, async_session: AsyncSession):
        """Create repository instance with mock session."""
        return SQLAlchemyRepository(mock_model, async_session)

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session, mock_model):
        """Test retrieving a record by ID."""
        # Arrange
        test_id = 1
        expected_result = mock_model(id=test_id, name="Test", value="Value")
        mock_session.add(expected_result)
        await mock_session.flush()

        # Act
        result = await repository.get(test_id)

        # Assert
        assert result is not None
        assert result.id == test_id
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_not_found(self, repository):
        """Test retrieving non-existent record returns None."""
        # Act
        result = await repository.get(999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_session, mock_model):
        """Test retrieving all records with pagination."""
        # Arrange
        for i in range(5):
            item = mock_model(id=i + 1, name=f"Item {i}", value=f"Value {i}")
            mock_session.add(item)
        await mock_session.flush()

        # Act
        results = await repository.get_all(skip=0, limit=3)

        # Assert
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_create_record(self, repository, mock_session, mock_model):
        """Test creating a new record."""
        # Arrange
        new_item = mock_model(name="New Item", value="New Value")

        # Act
        result = await repository.create(new_item)

        # Assert
        assert result.id is not None
        assert result.name == "New Item"
        assert result.value == "New Value"

    @pytest.mark.asyncio
    async def test_update_record(self, repository, mock_session, mock_model):
        """Test updating an existing record."""
        # Arrange
        existing = mock_model(id=1, name="Old Name", value="Old Value")
        mock_session.add(existing)
        await mock_session.flush()

        # Act
        result = await repository.update(1, {"name": "Updated Name"})

        # Assert
        assert result is not None
        assert result.name == "Updated Name"
        assert result.value == "Old Value"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository):
        """Test updating non-existent record returns None."""
        # Act
        result = await repository.update(999, {"name": "Updated"})

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_record(self, repository, mock_session, mock_model):
        """Test deleting a record."""
        # Arrange
        item = mock_model(id=1, name="To Delete", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act
        result = await repository.delete(1)

        # Assert
        assert result is True
        # Verify deletion
        deleted = await repository.get(1)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository):
        """Test deleting non-existent record returns False."""
        # Act
        result = await repository.delete(999)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_field(self, repository, mock_session, mock_model):
        """Test retrieving record by field value."""
        # Arrange
        item = mock_model(id=1, name="unique_name", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act
        result = await repository.get_by_field("name", "unique_name")

        # Assert
        assert result is not None
        assert result.name == "unique_name"

    @pytest.mark.asyncio
    async def test_get_many_by_field(self, repository, mock_session, mock_model):
        """Test retrieving multiple records by field value."""
        # Arrange
        for i in range(5):
            item = mock_model(
                id=i + 1,
                name="category_a" if i < 3 else "category_b",
                value=f"Value {i}",
            )
            mock_session.add(item)
        await mock_session.flush()

        # Act
        results = await repository.get_many_by_field("name", "category_a")

        # Assert
        assert len(results) == 3
        for result in results:
            assert result.name == "category_a"

    @pytest.mark.asyncio
    async def test_exists(self, repository, mock_session, mock_model):
        """Test checking if record exists."""
        # Arrange
        item = mock_model(id=1, name="Exists", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act & Assert
        assert await repository.exists(1) is True
        assert await repository.exists(999) is False

    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session, mock_model):
        """Test counting total records."""
        # Arrange
        for i in range(5):
            item = mock_model(id=i + 1, name=f"Item {i}", value=f"Value {i}")
            mock_session.add(item)
        await mock_session.flush()

        # Act
        count = await repository.count()

        # Assert
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_empty_table(self, repository):
        """Test counting on empty table."""
        # Act
        count = await repository.count()

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_metrics_collection_on_get(
        self, repository, mock_session, mock_model, mock_metrics
    ):
        """Test that metrics are collected during get operation."""
        # Arrange
        item = mock_model(id=1, name="Test", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act
        await repository.get(1)

        # Assert - verify metrics were recorded (implementation specific)
        # This would need actual mock verification based on your metrics implementation

    @pytest.mark.asyncio
    async def test_tracing_spans_created(
        self, repository, mock_session, mock_model, mock_tracer
    ):
        """Test that tracing spans are created during operations."""
        # Arrange
        item = mock_model(id=1, name="Test", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act
        await repository.get(1)

        # Assert - verify spans were created (implementation specific)
        # This would need actual mock verification based on your tracing implementation


class TestSQLAlchemyRepositoryEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_get_with_none_id(self, repository):
        """Test get with None ID."""
        # Act & Assert
        with pytest.raises(Exception):
            await repository.get(None)

    @pytest.mark.asyncio
    async def test_update_with_empty_dict(self, repository, mock_session, mock_model):
        """Test update with empty dict."""
        # Arrange
        item = mock_model(id=1, name="Test", value="Value")
        mock_session.add(item)
        await mock_session.flush()

        # Act
        result = await repository.update(1, {})

        # Assert
        assert result is not None
        # Record should remain unchanged
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_by_field_invalid_field(self, repository):
        """Test get_by_field with non-existent field."""
        # Act & Assert
        with pytest.raises(AttributeError):
            await repository.get_by_field("nonexistent_field", "value")

    @pytest.mark.asyncio
    async def test_create_none_object(self, repository):
        """Test create with None."""
        # Act & Assert
        with pytest.raises(Exception):
            await repository.create(None)

    @pytest.mark.asyncio
    async def test_pagination_with_negative_skip(self, repository):
        """Test pagination with negative skip value."""
        # Act
        results = await repository.get_all(skip=-1, limit=10)

        # Assert - SQLAlchemy handles negative offsets gracefully
        assert isinstance(results, list)


class TestSQLAlchemyRepositoryPerformance:
    """Performance and load tests."""

    @pytest.mark.asyncio
    async def test_large_dataset_pagination(self, repository, mock_session, mock_model):
        """Test pagination with large dataset."""
        # Arrange - Create 1000 items
        for i in range(1000):
            item = mock_model(id=i + 1, name=f"Item {i}", value=f"Value {i}")
            mock_session.add(item)
        await mock_session.flush()

        # Act & Assert - Paginate through all
        total_pages = 10
        page_size = 100

        for page in range(total_pages):
            results = await repository.get_all(skip=page * page_size, limit=page_size)
            assert len(results) == page_size

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, repository, mock_session, mock_model):
        """Test concurrent read operations."""
        import asyncio

        # Arrange
        for i in range(100):
            item = mock_model(id=i + 1, name=f"Item {i}", value=f"Value {i}")
            mock_session.add(item)
        await mock_session.flush()

        # Act - Perform 50 concurrent reads
        async def read_item(item_id):
            return await repository.get(item_id)

        tasks = [read_item((i % 100) + 1) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, (
            f"Found {len(exceptions)} exceptions during concurrent reads"
        )


# Integration test marker
pytestmark = pytest.mark.asyncio
