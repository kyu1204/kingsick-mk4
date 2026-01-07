"""
Unit tests for main FastAPI application.
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Test suite for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, client: AsyncClient) -> None:
        """Test that health check endpoint returns 200 OK."""
        response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_returns_status_ok(self, client: AsyncClient) -> None:
        """Test that health check returns status: ok in response."""
        response = await client.get("/health")
        data = response.json()

        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_includes_app_name(self, client: AsyncClient) -> None:
        """Test that health check includes application name."""
        response = await client.get("/health")
        data = response.json()

        assert "app" in data
        assert data["app"] == "KingSick"


class TestAppConfiguration:
    """Test suite for FastAPI app configuration."""

    def test_app_has_cors_middleware(self) -> None:
        """Test that CORS middleware is configured."""
        from app.main import app

        middleware_classes = [m.cls.__name__ for m in app.user_middleware]

        assert "CORSMiddleware" in middleware_classes

    def test_app_has_title(self) -> None:
        """Test that app has a title configured."""
        from app.main import app

        assert app.title == "KingSick API"

    def test_app_has_version(self) -> None:
        """Test that app has a version configured."""
        from app.main import app

        assert app.version is not None


class TestRootEndpoint:
    """Test suite for root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_welcome_message(self, client: AsyncClient) -> None:
        """Test that root endpoint returns welcome message."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
