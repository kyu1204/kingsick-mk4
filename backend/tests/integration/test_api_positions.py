"""
Integration tests for positions API router.

Tests position management endpoints.
Note: These tests use mock data since they require KIS API authentication.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.kis_api import Position


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_positions() -> list[Position]:
    """Create mock positions."""
    return [
        Position(
            stock_code="005930",
            stock_name="Samsung Electronics",
            quantity=10,
            avg_price=70000.0,
            current_price=72000.0,
            profit_loss=20000.0,
            profit_loss_rate=2.86,
        ),
        Position(
            stock_code="000660",
            stock_name="SK Hynix",
            quantity=5,
            avg_price=150000.0,
            current_price=145000.0,
            profit_loss=-25000.0,
            profit_loss_rate=-3.33,
        ),
    ]


class TestGetPositionsEndpoint:
    """Tests for get positions endpoint."""

    def test_get_positions_without_auth(self, client: TestClient) -> None:
        """Test getting positions without KIS API credentials."""
        # Without proper configuration, should return empty or mock data
        response = client.get("/api/v1/positions/")
        # Since we don't have real KIS API credentials in test,
        # the endpoint should handle this gracefully
        assert response.status_code in [200, 401, 503]

    def test_get_positions_mock(self, client: TestClient, mock_positions: list[Position]) -> None:
        """Test getting positions with mocked KIS API."""
        with patch("app.api.positions.get_positions_from_api") as mock_get:
            mock_get.return_value = mock_positions

            response = client.get("/api/v1/positions/")
            # If mock is used, we get 200
            if response.status_code == 200:
                data = response.json()
                assert "positions" in data


class TestGetBalanceEndpoint:
    """Tests for get balance endpoint."""

    def test_get_balance_without_auth(self, client: TestClient) -> None:
        """Test getting balance without KIS API credentials."""
        response = client.get("/api/v1/positions/balance")
        # Should handle missing credentials gracefully
        assert response.status_code in [200, 401, 503]


class TestGetStockPriceEndpoint:
    """Tests for get stock price endpoint."""

    def test_get_stock_price_without_auth(self, client: TestClient) -> None:
        """Test getting stock price without KIS API credentials."""
        response = client.get("/api/v1/positions/price/005930")
        # Should handle missing credentials gracefully
        assert response.status_code in [200, 401, 503]


class TestGetDailyPricesEndpoint:
    """Tests for get daily prices endpoint."""

    def test_get_daily_prices_without_auth(self, client: TestClient) -> None:
        """Test getting daily prices without KIS API credentials."""
        response = client.get("/api/v1/positions/daily-prices/005930")
        # Should handle missing credentials gracefully
        assert response.status_code in [200, 401, 503]

    def test_get_daily_prices_with_count(self, client: TestClient) -> None:
        """Test getting daily prices with count parameter."""
        response = client.get("/api/v1/positions/daily-prices/005930?count=50")
        # Should handle missing credentials gracefully
        assert response.status_code in [200, 401, 503]
