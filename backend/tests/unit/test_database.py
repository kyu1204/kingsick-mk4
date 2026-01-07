"""
Unit tests for database module.
"""

import pytest


class TestDatabaseConfiguration:
    """Test suite for database configuration."""

    def test_engine_is_async(self) -> None:
        """Test that the database engine is configured for async operations."""
        from app.database import engine

        # AsyncEngine should have async-specific attributes
        assert hasattr(engine, "begin")
        assert hasattr(engine, "connect")

    def test_async_session_maker_exists(self) -> None:
        """Test that async session maker is configured."""
        from app.database import async_session_maker

        assert async_session_maker is not None

    def test_base_model_exists(self) -> None:
        """Test that Base model class exists for ORM models."""
        from app.database import Base

        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_get_db_is_async_generator(self) -> None:
        """Test that get_db returns an async generator."""
        import inspect

        from app.database import get_db

        assert inspect.isasyncgenfunction(get_db)

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        """Test that get_db yields an async session."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.database import get_db

        async for session in get_db():
            assert isinstance(session, AsyncSession)
            break  # Only need to test the first yield


class TestDatabaseConnection:
    """Test suite for database connection handling."""

    def test_database_url_is_postgresql(self) -> None:
        """Test that database URL is configured for PostgreSQL."""
        from app.config import get_settings

        settings = get_settings()

        assert "postgresql" in settings.database_url

    def test_database_url_uses_asyncpg(self) -> None:
        """Test that database URL uses asyncpg driver."""
        from app.config import get_settings

        settings = get_settings()

        assert "asyncpg" in settings.database_url
