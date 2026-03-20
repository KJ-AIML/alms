"""
Tests for SQLAlchemy repository implementation.

These tests use mocked sessions to avoid database dependencies.
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from src.database.repositories.sqlalchemy_repository import SQLAlchemyRepository


Base = declarative_base()


class SampleModel(Base):
    """Sample SQLAlchemy model for testing."""

    __tablename__ = "sample_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    value = Column(String(50))


class TestSQLAlchemyRepository:
    """Test suite for SQLAlchemyRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return SQLAlchemyRepository(SampleModel, mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session):
        """Test retrieving a record by ID."""
        # Arrange
        expected_result = SampleModel(id=1, name="Test", value="Value")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_result
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get(1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == "Test"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_not_found(self, repository, mock_session):
        """Test retrieving non-existent record returns None."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get(999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_session):
        """Test retrieving all records with pagination."""
        # Arrange
        items = [
            SampleModel(id=1, name="Item 1", value="Value 1"),
            SampleModel(id=2, name="Item 2", value="Value 2"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = items
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_all(skip=0, limit=10)

        # Assert
        assert len(results) == 2
        assert results[0].name == "Item 1"

    @pytest.mark.asyncio
    async def test_create_record(self, repository, mock_session):
        """Test creating a new record."""
        # Arrange
        new_item = SampleModel(name="New Item", value="New Value")

        # Act
        result = await repository.create(new_item)

        # Assert
        mock_session.add.assert_called_once_with(new_item)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(new_item)

    @pytest.mark.asyncio
    async def test_update_record(self, repository, mock_session):
        """Test updating an existing record."""
        # Arrange
        existing = SampleModel(id=1, name="Old Name", value="Old Value")

        # Mock get to return the existing record
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.update(1, {"name": "Updated Name"})

        # Assert
        mock_session.execute.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_delete_record(self, repository, mock_session):
        """Test deleting a record."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test deleting non-existent record returns False."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.delete(999)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_field(self, repository, mock_session):
        """Test retrieving record by field value."""
        # Arrange
        expected = SampleModel(id=1, name="unique_name", value="Value")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_field("name", "unique_name")

        # Assert
        assert result is not None
        assert result.name == "unique_name"

    @pytest.mark.asyncio
    async def test_exists(self, repository, mock_session):
        """Test checking if record exists."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = SampleModel(id=1)
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.exists(1)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session):
        """Test counting total records."""
        # Arrange
        items = [SampleModel(id=i) for i in range(5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = items
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.count()

        # Assert
        assert result == 5


class TestSQLAlchemyRepositoryEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_get_with_invalid_id(self, mock_session):
        """Test get with invalid ID."""
        # Arrange
        repository = SQLAlchemyRepository(SampleModel, mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get(-1)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_create_with_none_values(self, mock_session):
        """Test create with None values."""
        # Arrange
        repository = SQLAlchemyRepository(SampleModel, mock_session)
        item = SampleModel(name=None, value=None)

        # Act
        result = await repository.create(item)

        # Assert - should not raise
        mock_session.add.assert_called_once_with(item)


pytestmark = pytest.mark.asyncio
