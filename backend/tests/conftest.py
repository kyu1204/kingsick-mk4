"""
Pytest configuration and fixtures for KingSick backend tests.
"""

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app modules
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/kingsick_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-bytes-00")


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for the FastAPI app.
    """
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def test_settings() -> dict[str, Any]:
    """
    Return test settings dictionary.
    """
    return {
        "environment": "test",
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/kingsick_test",
        "redis_url": "redis://localhost:6379/1",
        "jwt_secret": "test-secret-key-for-testing-only",
    }
