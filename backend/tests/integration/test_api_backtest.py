import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User
from app.models.backtest import BacktestResult as BacktestResultModel
from app.models.backtest import StockPrice
from app.services.auth import create_access_token


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
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_stock_prices():
    base_date = date(2025, 1, 1)
    prices = []
    for i in range(60):
        d = base_date + timedelta(days=i)
        price = MagicMock(spec=StockPrice)
        price.trade_date = d
        price.open_price = 50000.0
        price.high_price = 51000.0
        price.low_price = 49000.0
        price.close_price = 50000.0 + (i * 100)
        price.volume = 1000000
        prices.append(price)
    return prices


@pytest.fixture
def mock_backtest_result(mock_user):
    result = MagicMock(spec=BacktestResultModel)
    result.id = uuid.uuid4()
    result.user_id = mock_user.id
    result.name = "Test Backtest"
    result.config = {
        "stock_codes": ["005930"],
        "initial_capital": 10000000,
    }
    result.result = {
        "start_date": "2025-01-01",
        "end_date": "2025-02-28",
        "initial_capital": 10000000,
        "final_capital": 10500000,
        "total_return_pct": 5.0,
        "cagr": 30.0,
        "mdd": 3.0,
        "sharpe_ratio": 1.5,
        "win_rate": 60.0,
        "profit_factor": 2.0,
        "total_trades": 10,
        "winning_trades": 6,
        "losing_trades": 4,
        "avg_win": 100000,
        "avg_loss": -50000,
        "max_win": 200000,
        "max_loss": -80000,
        "daily_equity": [10000000, 10100000, 10200000],
        "daily_returns": [1.0, 0.99],
        "drawdown_curve": [0.0, 0.5, 1.0],
    }
    result.created_at = datetime.now(UTC)
    result.trades = []
    return result


class TestBacktestRunAPI:
    @pytest.mark.asyncio
    async def test_run_backtest_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/backtest/run",
                json={
                    "stock_codes": ["005930"],
                    "start_date": "2025-01-01",
                    "end_date": "2025-02-28",
                },
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_run_backtest_invalid_dates(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/backtest/run",
                    headers=auth_headers,
                    json={
                        "stock_codes": ["005930"],
                        "start_date": "2025-02-28",
                        "end_date": "2025-01-01",
                    },
                )
                assert response.status_code == 400
                assert "start_date must be before end_date" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_run_backtest_no_price_data(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.backtest.PriceHistoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_prices = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/v1/backtest/run",
                        headers=auth_headers,
                        json={
                            "stock_codes": ["005930"],
                            "start_date": "2025-01-01",
                            "end_date": "2025-02-28",
                        },
                    )
                    assert response.status_code == 400
                    assert "No price data found" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_run_backtest_success(self, mock_user, mock_db, auth_headers, mock_stock_prices):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.backtest.PriceHistoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_prices = AsyncMock(return_value=mock_stock_prices)
            mock_service_class.return_value = mock_service

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/v1/backtest/run",
                        headers=auth_headers,
                        json={
                            "stock_codes": ["005930"],
                            "start_date": "2025-01-01",
                            "end_date": "2025-02-28",
                            "name": "Test Backtest",
                            "initial_capital": 10000000,
                        },
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert "id" in data
                    assert data["initial_capital"] == 10000000
                    assert "total_return_pct" in data
                    assert "sharpe_ratio" in data
                    assert "daily_equity" in data
            finally:
                app.dependency_overrides.clear()


class TestBacktestResultsAPI:
    @pytest.mark.asyncio
    async def test_list_results_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/backtest/results")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_results_empty(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/backtest/results",
                    headers=auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["count"] == 0
                assert data["results"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_results_with_data(
        self, mock_user, mock_db, auth_headers, mock_backtest_result
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_backtest_result]
        mock_db.execute = AsyncMock(return_value=mock_result)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/backtest/results",
                    headers=auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["count"] == 1
                assert data["results"][0]["name"] == "Test Backtest"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                test_id = str(uuid.uuid4())
                response = await client.get(
                    f"/api/v1/backtest/results/{test_id}",
                    headers=auth_headers,
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_result_invalid_id(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/backtest/results/invalid-id",
                    headers=auth_headers,
                )
                assert response.status_code == 400
                assert "Invalid backtest ID format" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_result_success(self, mock_user, mock_db, auth_headers, mock_backtest_result):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backtest_result
        mock_trades_result = MagicMock()
        mock_trades_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_trades_result])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"/api/v1/backtest/results/{mock_backtest_result.id}",
                    headers=auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Backtest"
                assert data["total_return_pct"] == 5.0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_result_not_found(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                test_id = str(uuid.uuid4())
                response = await client.delete(
                    f"/api/v1/backtest/results/{test_id}",
                    headers=auth_headers,
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_result_success(
        self, mock_user, mock_db, auth_headers, mock_backtest_result
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backtest_result
        mock_db.execute = AsyncMock(return_value=mock_result)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.delete(
                    f"/api/v1/backtest/results/{mock_backtest_result.id}",
                    headers=auth_headers,
                )
                assert response.status_code == 204
                mock_db.delete.assert_called_once()
                mock_db.commit.assert_called()
        finally:
            app.dependency_overrides.clear()
