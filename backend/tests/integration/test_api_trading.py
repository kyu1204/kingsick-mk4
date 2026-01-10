"""
Integration tests for trading API router.

Tests trading operations endpoints including mode management and alerts.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User
from app.services.kis_api import (
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderStatusResult,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestTradingStatusEndpoint:
    """Tests for trading status endpoint."""

    def test_get_trading_status(self, client: TestClient) -> None:
        """Test getting trading status."""
        response = client.get("/api/v1/trading/status")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert data["mode"] in ["AUTO", "ALERT"]
        assert "pending_alerts_count" in data
        assert "trailing_stops_count" in data


class TestSetModeEndpoint:
    """Tests for set mode endpoint."""

    def test_set_mode_to_auto(self, client: TestClient) -> None:
        """Test setting mode to AUTO."""
        response = client.post(
            "/api/v1/trading/mode",
            json={"mode": "AUTO"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "AUTO"

    def test_set_mode_to_alert(self, client: TestClient) -> None:
        """Test setting mode to ALERT."""
        response = client.post(
            "/api/v1/trading/mode",
            json={"mode": "ALERT"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "ALERT"

    def test_set_invalid_mode(self, client: TestClient) -> None:
        """Test setting invalid mode."""
        response = client.post(
            "/api/v1/trading/mode",
            json={"mode": "INVALID"},
        )
        assert response.status_code == 422  # Validation error


class TestPendingAlertsEndpoint:
    """Tests for pending alerts endpoint."""

    def test_get_pending_alerts_empty(self, client: TestClient) -> None:
        """Test getting pending alerts when none exist."""
        response = client.get("/api/v1/trading/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)


class TestApproveAlertEndpoint:
    """Tests for approve alert endpoint."""

    def test_approve_nonexistent_alert(self, client: TestClient) -> None:
        """Test approving an alert that doesn't exist."""
        response = client.post(
            "/api/v1/trading/alerts/approve",
            json={"alert_id": "nonexistent-alert-id"},
        )
        assert response.status_code == 404


class TestRejectAlertEndpoint:
    """Tests for reject alert endpoint."""

    def test_reject_nonexistent_alert(self, client: TestClient) -> None:
        """Test rejecting an alert that doesn't exist."""
        response = client.post(
            "/api/v1/trading/alerts/reject",
            json={"alert_id": "nonexistent-alert-id"},
        )
        assert response.status_code == 404


class TestRiskCheckEndpoint:
    """Tests for risk check endpoint."""

    def test_risk_check_hold(self, client: TestClient) -> None:
        """Test risk check that should return HOLD."""
        response = client.post(
            "/api/v1/trading/risk/check",
            json={
                "entry_price": 100.0,
                "current_price": 102.0,  # 2% profit - within limits
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "HOLD"
        assert "current_profit_pct" in data

    def test_risk_check_stop_loss(self, client: TestClient) -> None:
        """Test risk check that should trigger stop-loss."""
        response = client.post(
            "/api/v1/trading/risk/check",
            json={
                "entry_price": 100.0,
                "current_price": 90.0,  # -10% loss - should trigger stop-loss
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "STOP_LOSS"

    def test_risk_check_take_profit(self, client: TestClient) -> None:
        """Test risk check that should trigger take-profit."""
        response = client.post(
            "/api/v1/trading/risk/check",
            json={
                "entry_price": 100.0,
                "current_price": 115.0,  # +15% profit - should trigger take-profit
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "TAKE_PROFIT"


class TestPositionSizeEndpoint:
    """Tests for position size calculation endpoint."""

    def test_calculate_position_size(self, client: TestClient) -> None:
        """Test position size calculation."""
        response = client.post(
            "/api/v1/trading/risk/position-size",
            json={
                "available_capital": 10_000_000.0,
                "stock_price": 50_000.0,
                "risk_per_trade_pct": 2.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "quantity" in data
        assert isinstance(data["quantity"], int)
        assert data["quantity"] >= 0

    def test_calculate_position_size_zero_price(self, client: TestClient) -> None:
        """Test position size with zero price (validation error)."""
        response = client.post(
            "/api/v1/trading/risk/position-size",
            json={
                "available_capital": 10_000_000.0,
                "stock_price": 0.0,  # Invalid
                "risk_per_trade_pct": 2.0,
            },
        )
        assert response.status_code == 422


class TestCanOpenPositionEndpoint:
    """Tests for can open position check endpoint."""

    def test_can_open_position_allowed(self, client: TestClient) -> None:
        """Test position opening when allowed."""
        response = client.post(
            "/api/v1/trading/risk/can-open",
            json={
                "investment_amount": 500_000.0,
                "current_positions_count": 3,
                "daily_pnl_pct": 2.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["can_open"] is True
        assert data["reason"] == ""

    def test_can_open_position_daily_loss_exceeded(self, client: TestClient) -> None:
        """Test position opening when daily loss limit exceeded."""
        response = client.post(
            "/api/v1/trading/risk/can-open",
            json={
                "investment_amount": 500_000.0,
                "current_positions_count": 3,
                "daily_pnl_pct": -15.0,  # Exceeds -10% daily loss limit
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["can_open"] is False
        assert "일일 손실 한도" in data["reason"]


class TestOrderStatusEndpoint:

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = "user-123"
        user.email = "test@example.com"
        user.is_admin = False
        return user

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    def test_get_order_status_not_authenticated(self, client: TestClient) -> None:
        response = client.get("/api/v1/trading/orders/0000123456/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_order_status_no_api_key(self, mock_user, mock_db) -> None:
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get("/api/v1/trading/orders/0000123456/status")
                assert response.status_code == 400
                assert "not configured" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_order_status_success_filled(self, mock_user, mock_db) -> None:
        mock_api_key_record = MagicMock()
        mock_api_key_record.kis_app_key_encrypted = "encrypted_key"
        mock_api_key_record.kis_app_secret_encrypted = "encrypted_secret"
        mock_api_key_record.kis_account_no_encrypted = "encrypted_account"
        mock_api_key_record.is_paper_trading = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key_record
        mock_db.execute = AsyncMock(return_value=mock_result)

        order_status_result = OrderStatusResult(
            order_id="0000123456",
            stock_code="005930",
            stock_name="삼성전자",
            order_side=OrderSide.BUY,
            order_quantity=10,
            filled_quantity=10,
            filled_price=50000.0,
            order_status=OrderStatus.FILLED,
            order_time="093000",
            filled_time="093015",
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch("app.api.trading.decrypt", side_effect=lambda x: f"decrypted_{x}"):
                with patch("app.api.trading.KISApiClient") as mock_kis:
                    mock_client_instance = AsyncMock()
                    mock_client_instance.authenticate.return_value = True
                    mock_client_instance.get_order_status.return_value = order_status_result
                    mock_client_instance.__aenter__.return_value = mock_client_instance
                    mock_client_instance.__aexit__.return_value = None
                    mock_kis.return_value = mock_client_instance

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as ac:
                        response = await ac.get("/api/v1/trading/orders/0000123456/status")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["order_id"] == "0000123456"
                        assert data["stock_code"] == "005930"
                        assert data["side"] == "BUY"
                        assert data["status"] == "FILLED"
                        assert data["filled_quantity"] == 10
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_order_status_not_found(self, mock_user, mock_db) -> None:
        mock_api_key_record = MagicMock()
        mock_api_key_record.kis_app_key_encrypted = "encrypted_key"
        mock_api_key_record.kis_app_secret_encrypted = "encrypted_secret"
        mock_api_key_record.kis_account_no_encrypted = "encrypted_account"
        mock_api_key_record.is_paper_trading = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key_record
        mock_db.execute = AsyncMock(return_value=mock_result)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch("app.api.trading.decrypt", side_effect=lambda x: f"decrypted_{x}"):
                with patch("app.api.trading.KISApiClient") as mock_kis:
                    mock_client_instance = AsyncMock()
                    mock_client_instance.authenticate.return_value = True
                    mock_client_instance.get_order_status.return_value = None
                    mock_client_instance.__aenter__.return_value = mock_client_instance
                    mock_client_instance.__aexit__.return_value = None
                    mock_kis.return_value = mock_client_instance

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as ac:
                        response = await ac.get("/api/v1/trading/orders/NONEXISTENT/status")
                        assert response.status_code == 200
                        assert response.json() is None
        finally:
            app.dependency_overrides.clear()
