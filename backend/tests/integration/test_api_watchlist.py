import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User, WatchlistItem
from app.services.auth import create_access_token
from app.services.watchlist import WatchlistError, WatchlistService


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def auth_headers(mock_user):
    access_token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_watchlist_item(mock_user):
    from datetime import UTC, datetime

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
    item.created_at = datetime.now(UTC)
    item.updated_at = datetime.now(UTC)
    return item


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_watchlist_service():
    return MagicMock(spec=WatchlistService)


class TestGetWatchlist:
    @pytest.mark.asyncio
    async def test_get_watchlist_success(
        self, mock_user, mock_watchlist_item, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.get_user_items = AsyncMock(return_value=[mock_watchlist_item])

        def override_get_current_user():
            return mock_user

        def override_get_db():
            return mock_db

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.get("/api/v1/watchlist", headers=auth_headers)

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_watchlist_unauthorized(self):
        app.dependency_overrides.clear()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/watchlist")
        assert response.status_code == 401


class TestAddWatchlistItem:
    @pytest.mark.asyncio
    async def test_add_item_success(
        self, mock_user, mock_watchlist_item, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.create_item = AsyncMock(return_value=mock_watchlist_item)
        mock_db.commit = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.post(
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

        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["stock_code"] == "005930"

    @pytest.mark.asyncio
    async def test_add_item_invalid_stock_code(self, mock_user, auth_headers, mock_db):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/watchlist",
                headers=auth_headers,
                json={
                    "stock_code": "invalid",
                    "stock_name": "Test",
                },
            )

        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_item_duplicate(
        self, mock_user, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.create_item = AsyncMock(
            side_effect=WatchlistError("Stock 005930 already in watchlist")
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.post(
                    "/api/v1/watchlist",
                    headers=auth_headers,
                    json={
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                    },
                )

        app.dependency_overrides.clear()
        assert response.status_code == 400


class TestUpdateWatchlistItem:
    @pytest.mark.asyncio
    async def test_update_item_success(
        self, mock_user, mock_watchlist_item, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_item.target_price = Decimal("85000")
        mock_watchlist_service.update_item = AsyncMock(return_value=mock_watchlist_item)
        mock_db.commit = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.put(
                    f"/api/v1/watchlist/{mock_watchlist_item.id}",
                    headers=auth_headers,
                    json={"target_price": 85000},
                )

        app.dependency_overrides.clear()
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_item_not_found(
        self, mock_user, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.update_item = AsyncMock(
            side_effect=WatchlistError("Watchlist item not found")
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        random_id = uuid.uuid4()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.put(
                    f"/api/v1/watchlist/{random_id}",
                    headers=auth_headers,
                    json={"target_price": 85000},
                )

        app.dependency_overrides.clear()
        assert response.status_code == 404


class TestToggleWatchlistItem:
    @pytest.mark.asyncio
    async def test_toggle_item_success(
        self, mock_user, mock_watchlist_item, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_item.is_active = False
        mock_watchlist_service.toggle_active = AsyncMock(return_value=mock_watchlist_item)
        mock_db.commit = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.patch(
                    f"/api/v1/watchlist/{mock_watchlist_item.id}/toggle",
                    headers=auth_headers,
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestDeleteWatchlistItem:
    @pytest.mark.asyncio
    async def test_delete_item_success(
        self, mock_user, mock_watchlist_item, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.delete_item = AsyncMock(return_value=True)
        mock_db.commit = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.watchlist.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.delete(
                    f"/api/v1/watchlist/{mock_watchlist_item.id}",
                    headers=auth_headers,
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200


class TestTradingTargets:
    @pytest.mark.asyncio
    async def test_get_trading_targets_success(
        self, mock_user, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.get_active_stock_codes = AsyncMock(
            return_value=["005930", "000660"]
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.trading.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.get(
                    "/api/v1/trading/targets", headers=auth_headers
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "stock_codes" in data
        assert data["total"] == 2
        assert "005930" in data["stock_codes"]

    @pytest.mark.asyncio
    async def test_get_trading_targets_unauthorized(self):
        app.dependency_overrides.clear()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/trading/targets")
        assert response.status_code == 401


class TestTradingSettings:
    @pytest.mark.asyncio
    async def test_get_trading_settings_success(
        self, mock_user, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.get_trading_settings = AsyncMock(
            return_value={
                "target_price": 80000.0,
                "stop_loss_price": 70000.0,
                "quantity": 10,
            }
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.trading.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.get(
                    "/api/v1/trading/settings/005930", headers=auth_headers
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["target_price"] == 80000.0
        assert data["stop_loss_price"] == 70000.0
        assert data["quantity"] == 10

    @pytest.mark.asyncio
    async def test_get_trading_settings_not_found(
        self, mock_user, auth_headers, mock_db, mock_watchlist_service
    ):
        mock_watchlist_service.get_trading_settings = AsyncMock(return_value=None)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    "app.api.trading.WatchlistService",
                    lambda db: mock_watchlist_service,
                )
                response = await client.get(
                    "/api/v1/trading/settings/999999", headers=auth_headers
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() is None
