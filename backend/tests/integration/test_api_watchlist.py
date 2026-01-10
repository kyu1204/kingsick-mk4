"""
Integration tests for watchlist API endpoints.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, WatchlistItem
from app.services.auth import create_access_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def auth_headers(mock_user):
    """Create authorization headers with valid token."""
    access_token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_watchlist_item(mock_user):
    """Create a mock watchlist item."""
    item = MagicMock(spec=WatchlistItem)
    item.id = uuid.uuid4()
    item.user_id = mock_user.id
    item.stock_code = "005930"
    item.stock_name = "삼성전자"
    item.target_price = Decimal("80000")
    item.stop_loss_price = Decimal("70000")
    item.quantity = 10
    item.memo = "Test memo"
    item.is_active = True
    return item


class TestGetWatchlist:
    """Tests for GET /api/v1/watchlist."""

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_get_watchlist_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_watchlist_item, auth_headers
    ):
        """Get watchlist should return user's items."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_user_items = AsyncMock(return_value=[mock_watchlist_item])
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 1

    def test_get_watchlist_unauthorized(self, client):
        """Get watchlist without token should return 401."""
        response = client.get("/api/v1/watchlist")
        assert response.status_code == 401


class TestAddWatchlistItem:
    """Tests for POST /api/v1/watchlist."""

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_add_item_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_watchlist_item, auth_headers
    ):
        """Add item should return created item."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.create_item = AsyncMock(return_value=mock_watchlist_item)
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/watchlist",
            headers=auth_headers,
            json={
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "target_price": 80000,
                "stop_loss_price": 70000,
                "quantity": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["stock_code"] == "005930"

    def test_add_item_invalid_stock_code(self, client, auth_headers):
        """Invalid stock code should return 422."""
        response = client.post(
            "/api/v1/watchlist",
            headers=auth_headers,
            json={
                "stock_code": "invalid",
                "stock_name": "Test",
            },
        )

        assert response.status_code == 422

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_add_item_duplicate(
        self, mock_service_class, mock_get_user, client, mock_user, auth_headers
    ):
        """Adding duplicate stock should return 400."""
        from app.services.watchlist import WatchlistError

        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.create_item = AsyncMock(
            side_effect=WatchlistError("Stock 005930 already in watchlist")
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/watchlist",
            headers=auth_headers,
            json={
                "stock_code": "005930",
                "stock_name": "삼성전자",
            },
        )

        assert response.status_code == 400


class TestUpdateWatchlistItem:
    """Tests for PATCH /api/v1/watchlist/{item_id}."""

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_update_item_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_watchlist_item, auth_headers
    ):
        """Update item should return updated item."""
        mock_get_user.return_value = mock_user
        mock_watchlist_item.target_price = Decimal("85000")
        mock_service = MagicMock()
        mock_service.update_item = AsyncMock(return_value=mock_watchlist_item)
        mock_service_class.return_value = mock_service

        response = client.patch(
            f"/api/v1/watchlist/{mock_watchlist_item.id}",
            headers=auth_headers,
            json={"target_price": 85000},
        )

        assert response.status_code == 200

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_update_item_not_found(
        self, mock_service_class, mock_get_user, client, mock_user, auth_headers
    ):
        """Update non-existent item should return 404."""
        from app.services.watchlist import WatchlistError

        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.update_item = AsyncMock(
            side_effect=WatchlistError("Watchlist item not found")
        )
        mock_service_class.return_value = mock_service

        random_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/watchlist/{random_id}",
            headers=auth_headers,
            json={"target_price": 85000},
        )

        assert response.status_code == 404


class TestToggleWatchlistItem:
    """Tests for POST /api/v1/watchlist/{item_id}/toggle."""

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_toggle_item_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_watchlist_item, auth_headers
    ):
        """Toggle item should return toggled item."""
        mock_get_user.return_value = mock_user
        mock_watchlist_item.is_active = False
        mock_service = MagicMock()
        mock_service.toggle_active = AsyncMock(return_value=mock_watchlist_item)
        mock_service_class.return_value = mock_service

        response = client.post(
            f"/api/v1/watchlist/{mock_watchlist_item.id}/toggle",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestDeleteWatchlistItem:
    """Tests for DELETE /api/v1/watchlist/{item_id}."""

    @patch("app.api.watchlist.get_current_user")
    @patch("app.api.watchlist.WatchlistService")
    async def test_delete_item_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_watchlist_item, auth_headers
    ):
        """Delete item should return success."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.delete_item = AsyncMock(return_value=True)
        mock_service_class.return_value = mock_service

        response = client.delete(
            f"/api/v1/watchlist/{mock_watchlist_item.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestTradingTargets:
    """Tests for GET /api/v1/trading/targets."""

    @patch("app.api.trading.get_current_user")
    @patch("app.api.trading.WatchlistService")
    async def test_get_trading_targets_success(
        self, mock_service_class, mock_get_user, client, mock_user, auth_headers
    ):
        """Get trading targets should return stock codes."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_active_stock_codes = AsyncMock(return_value=["005930", "000660"])
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/trading/targets", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "stock_codes" in data
        assert data["total"] == 2
        assert "005930" in data["stock_codes"]

    def test_get_trading_targets_unauthorized(self, client):
        """Get trading targets without token should return 401."""
        response = client.get("/api/v1/trading/targets")
        assert response.status_code == 401


class TestTradingSettings:
    """Tests for GET /api/v1/trading/settings/{stock_code}."""

    @patch("app.api.trading.get_current_user")
    @patch("app.api.trading.WatchlistService")
    async def test_get_trading_settings_success(
        self, mock_service_class, mock_get_user, client, mock_user, auth_headers
    ):
        """Get trading settings should return stock settings."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trading_settings = AsyncMock(
            return_value={
                "target_price": 80000.0,
                "stop_loss_price": 70000.0,
                "quantity": 10,
            }
        )
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/trading/settings/005930", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["target_price"] == 80000.0
        assert data["stop_loss_price"] == 70000.0
        assert data["quantity"] == 10

    @patch("app.api.trading.get_current_user")
    @patch("app.api.trading.WatchlistService")
    async def test_get_trading_settings_not_found(
        self, mock_service_class, mock_get_user, client, mock_user, auth_headers
    ):
        """Get settings for non-existent stock should return null."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trading_settings = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/trading/settings/999999", headers=auth_headers)

        # None/null response
        assert response.status_code == 200
        assert response.json() is None
