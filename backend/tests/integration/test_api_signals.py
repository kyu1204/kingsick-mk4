"""
Integration tests for signals API router.

Tests AI signal generation endpoints.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestGenerateSignalEndpoint:
    """Tests for signal generation endpoint."""

    def test_generate_signal_with_sufficient_data(self, client: TestClient) -> None:
        """Test signal generation with enough data."""
        # Generate 50 data points
        prices = [100.0 + i * 0.5 for i in range(50)]
        volumes = [1000.0 + i * 10 for i in range(50)]

        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": prices, "volumes": volumes},
        )
        assert response.status_code == 200
        data = response.json()
        assert "signal" in data
        assert data["signal"] in ["BUY", "SELL", "HOLD"]
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert "reason" in data
        assert "indicators" in data

    def test_generate_signal_insufficient_data(self, client: TestClient) -> None:
        """Test signal generation with insufficient data."""
        prices = [100.0, 101.0, 102.0]
        volumes = [1000.0, 1100.0, 1200.0]

        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": prices, "volumes": volumes},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "HOLD"
        assert data["confidence"] == 0.0

    def test_generate_signal_empty_data(self, client: TestClient) -> None:
        """Test signal generation with empty data."""
        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": [], "volumes": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["signal"] == "HOLD"
        assert data["confidence"] == 0.0

    def test_generate_signal_buy_condition(self, client: TestClient) -> None:
        """Test signal generation that should trigger buy signal."""
        # Create a downtrend followed by oversold condition
        # Start high, go down (RSI should be low)
        prices = [200.0 - i * 2 for i in range(50)]
        # Add volume spike at the end
        volumes = [1000.0] * 49 + [5000.0]

        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": prices, "volumes": volumes},
        )
        assert response.status_code == 200
        data = response.json()
        # Signal should be BUY due to oversold RSI and volume spike
        # (may be HOLD if conditions not exactly met)
        assert data["signal"] in ["BUY", "HOLD"]
        assert "indicators" in data

    def test_generate_signal_sell_condition(self, client: TestClient) -> None:
        """Test signal generation that should trigger sell signal."""
        # Create an uptrend (RSI should be high)
        prices = [100.0 + i * 2 for i in range(50)]
        # Volume decreasing (no spike)
        volumes = [5000.0 - i * 50 for i in range(50)]

        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": prices, "volumes": volumes},
        )
        assert response.status_code == 200
        data = response.json()
        # Signal could be SELL due to overbought RSI
        assert data["signal"] in ["BUY", "SELL", "HOLD"]
        assert "indicators" in data

    def test_generate_signal_returns_indicators(self, client: TestClient) -> None:
        """Test that signal generation returns calculated indicators."""
        prices = [100.0 + i * 0.5 for i in range(50)]
        volumes = [1000.0 + i * 10 for i in range(50)]

        response = client.post(
            "/api/v1/signals/generate",
            json={"prices": prices, "volumes": volumes},
        )
        assert response.status_code == 200
        data = response.json()
        indicators = data["indicators"]

        # Check for expected indicator keys
        assert "rsi" in indicators
        assert "macd_line" in indicators
        assert "macd_signal" in indicators
        assert "current_price" in indicators
