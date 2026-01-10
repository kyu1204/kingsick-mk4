"""
Integration tests for indicators API router.

Tests technical indicator calculation endpoints.
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


class TestSMAEndpoint:
    """Tests for SMA endpoint."""

    def test_calculate_sma_success(self, client: TestClient) -> None:
        """Test successful SMA calculation."""
        response = client.post(
            "/api/v1/indicators/sma",
            json={
                "prices": [10.0, 11.0, 12.0, 13.0, 14.0],
                "period": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "values" in data
        assert len(data["values"]) == 5
        # First 2 values should be None (NaN)
        assert data["values"][0] is None
        assert data["values"][1] is None
        # Third value should be average of first 3
        assert data["values"][2] == pytest.approx(11.0, rel=1e-6)

    def test_calculate_sma_empty_prices(self, client: TestClient) -> None:
        """Test SMA with empty prices."""
        response = client.post(
            "/api/v1/indicators/sma",
            json={"prices": [], "period": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["values"] == []

    def test_calculate_sma_invalid_period(self, client: TestClient) -> None:
        """Test SMA with invalid period."""
        response = client.post(
            "/api/v1/indicators/sma",
            json={"prices": [10.0, 11.0], "period": 0},
        )
        assert response.status_code == 422  # Validation error


class TestEMAEndpoint:
    """Tests for EMA endpoint."""

    def test_calculate_ema_success(self, client: TestClient) -> None:
        """Test successful EMA calculation."""
        response = client.post(
            "/api/v1/indicators/ema",
            json={
                "prices": [10.0, 11.0, 12.0, 13.0, 14.0],
                "period": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "values" in data
        assert len(data["values"]) == 5


class TestRSIEndpoint:
    """Tests for RSI endpoint."""

    def test_calculate_rsi_success(self, client: TestClient) -> None:
        """Test successful RSI calculation."""
        # Generate price data with clear trend
        prices = [100.0 + i for i in range(20)]

        response = client.post(
            "/api/v1/indicators/rsi",
            json={"prices": prices, "period": 14},
        )
        assert response.status_code == 200
        data = response.json()
        assert "values" in data
        assert len(data["values"]) == 20

    def test_calculate_rsi_default_period(self, client: TestClient) -> None:
        """Test RSI with default period."""
        prices = [100.0 + i for i in range(20)]

        response = client.post(
            "/api/v1/indicators/rsi",
            json={"prices": prices},
        )
        assert response.status_code == 200


class TestMACDEndpoint:
    """Tests for MACD endpoint."""

    def test_calculate_macd_success(self, client: TestClient) -> None:
        """Test successful MACD calculation."""
        # Generate enough price data
        prices = [100.0 + i * 0.5 for i in range(50)]

        response = client.post(
            "/api/v1/indicators/macd",
            json={"prices": prices},
        )
        assert response.status_code == 200
        data = response.json()
        assert "macd_line" in data
        assert "signal_line" in data
        assert "histogram" in data

    def test_calculate_macd_custom_periods(self, client: TestClient) -> None:
        """Test MACD with custom periods."""
        prices = [100.0 + i * 0.5 for i in range(50)]

        response = client.post(
            "/api/v1/indicators/macd",
            json={
                "prices": prices,
                "fast": 8,
                "slow": 17,
                "signal": 9,
            },
        )
        assert response.status_code == 200


class TestBollingerBandsEndpoint:
    """Tests for Bollinger Bands endpoint."""

    def test_calculate_bollinger_bands_success(self, client: TestClient) -> None:
        """Test successful Bollinger Bands calculation."""
        prices = [100.0 + (i % 5) for i in range(30)]

        response = client.post(
            "/api/v1/indicators/bollinger-bands",
            json={"prices": prices, "period": 20, "std_dev": 2.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "upper" in data
        assert "middle" in data
        assert "lower" in data


class TestVolumeSpikeEndpoint:
    """Tests for volume spike endpoint."""

    def test_detect_volume_spike_success(self, client: TestClient) -> None:
        """Test successful volume spike detection."""
        volumes = [1000.0] * 19 + [5000.0]  # Spike at the end

        response = client.post(
            "/api/v1/indicators/volume-spike",
            json={"volumes": volumes, "threshold": 2.0, "lookback": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert "spikes" in data
        assert len(data["spikes"]) == 20
        # Last value should be a spike
        assert data["spikes"][-1] is True


class TestGoldenCrossEndpoint:
    """Tests for golden cross endpoint."""

    def test_detect_golden_cross(self, client: TestClient) -> None:
        """Test golden cross detection."""
        # Create prices that should trigger golden cross
        # Start with downtrend then reverse
        prices = [100.0 - i * 0.5 for i in range(15)] + [
            100.0 + i * 2.0 for i in range(10)
        ]

        response = client.post(
            "/api/v1/indicators/golden-cross",
            json={"prices": prices, "short_period": 5, "long_period": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert "detected" in data


class TestDeathCrossEndpoint:
    """Tests for death cross endpoint."""

    def test_detect_death_cross(self, client: TestClient) -> None:
        """Test death cross detection."""
        # Create prices that should trigger death cross
        prices = [100.0 + i * 0.5 for i in range(15)] + [
            100.0 - i * 2.0 for i in range(10)
        ]

        response = client.post(
            "/api/v1/indicators/death-cross",
            json={"prices": prices, "short_period": 5, "long_period": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert "detected" in data
