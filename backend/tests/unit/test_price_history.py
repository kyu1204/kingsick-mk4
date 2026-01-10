from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.price_history import PriceHistoryError, PriceHistoryService


class TestPriceHistoryService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_kis_client(self):
        client = AsyncMock()
        client.get_daily_prices = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_db):
        return PriceHistoryService(mock_db, kis_client=None)

    @pytest.fixture
    def service_with_kis(self, mock_db, mock_kis_client):
        return PriceHistoryService(mock_db, kis_client=mock_kis_client)

    @pytest.mark.asyncio
    async def test_get_prices_returns_empty_list_when_no_data(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        prices = await service.get_prices("005930", date(2025, 1, 1), date(2025, 12, 31))

        assert prices == []

    @pytest.mark.asyncio
    async def test_get_prices_returns_price_list(self, service, mock_db):
        mock_price = MagicMock()
        mock_price.stock_code = "005930"
        mock_price.trade_date = date(2025, 1, 2)
        mock_price.open_price = 71000.0
        mock_price.high_price = 72000.0
        mock_price.low_price = 70500.0
        mock_price.close_price = 71500.0
        mock_price.volume = 1000000

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_price]
        mock_db.execute.return_value = mock_result

        prices = await service.get_prices("005930", date(2025, 1, 1), date(2025, 1, 31))

        assert len(prices) == 1
        assert prices[0].stock_code == "005930"

    @pytest.mark.asyncio
    async def test_get_latest_date_returns_none_when_no_data(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_latest_date("005930")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_date_returns_date(self, service, mock_db):
        expected_date = date(2025, 12, 31)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_date
        mock_db.execute.return_value = mock_result

        result = await service.get_latest_date("005930")

        assert result == expected_date

    @pytest.mark.asyncio
    async def test_store_prices_returns_zero_for_empty_list(self, service):
        result = await service.store_prices([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_store_prices_commits_to_db(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        prices = [{
            "stock_code": "005930",
            "trade_date": date(2025, 1, 2),
            "open_price": 71000.0,
            "high_price": 72000.0,
            "low_price": 70500.0,
            "close_price": 71500.0,
            "volume": 1000000,
        }]

        result = await service.store_prices(prices)

        assert result == 1
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_store_raises_error_without_kis_client(self, service):
        with pytest.raises(PriceHistoryError, match="KIS client not configured"):
            await service.fetch_and_store("005930", days=100)

    @pytest.mark.asyncio
    async def test_fetch_and_store_calls_kis_api(self, service_with_kis, mock_kis_client, mock_db):
        mock_kis_client.get_daily_prices.return_value = [
            {
                "date": "20250102",
                "open": 71000.0,
                "high": 72000.0,
                "low": 70500.0,
                "close": 71500.0,
                "volume": 1000000,
            }
        ]
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = await service_with_kis.fetch_and_store("005930", days=100)

        mock_kis_client.get_daily_prices.assert_called_once_with("005930", count=100)
        assert result == 1

    @pytest.mark.asyncio
    async def test_fetch_and_store_skips_invalid_dates(self, service_with_kis, mock_kis_client, mock_db):
        mock_kis_client.get_daily_prices.return_value = [
            {"date": "invalid", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0},
            {"date": "20250102", "open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 1000000},
        ]
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = await service_with_kis.fetch_and_store("005930", days=100)

        assert result == 1

    @pytest.mark.asyncio
    async def test_get_price_dataframe_returns_dict_list(self, service, mock_db):
        mock_price = MagicMock()
        mock_price.trade_date = date(2025, 1, 2)
        mock_price.open_price = 71000.0
        mock_price.high_price = 72000.0
        mock_price.low_price = 70500.0
        mock_price.close_price = 71500.0
        mock_price.volume = 1000000

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_price]
        mock_db.execute.return_value = mock_result

        result = await service.get_price_dataframe("005930", date(2025, 1, 1), date(2025, 1, 31))

        assert len(result) == 1
        assert result[0]["date"] == date(2025, 1, 2)
        assert result[0]["close"] == 71500.0

    @pytest.mark.asyncio
    async def test_has_sufficient_data_returns_true(self, service, mock_db):
        mock_prices = [MagicMock() for _ in range(25)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_prices
        mock_db.execute.return_value = mock_result

        result = await service.has_sufficient_data("005930", date(2025, 1, 1), date(2025, 12, 31))

        assert result is True

    @pytest.mark.asyncio
    async def test_has_sufficient_data_returns_false(self, service, mock_db):
        mock_prices = [MagicMock() for _ in range(10)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_prices
        mock_db.execute.return_value = mock_result

        result = await service.has_sufficient_data("005930", date(2025, 1, 1), date(2025, 12, 31))

        assert result is False

    @pytest.mark.asyncio
    async def test_sync_latest_fetches_full_history_when_no_data(self, service_with_kis, mock_db, mock_kis_client):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        mock_kis_client.get_daily_prices.return_value = []

        await service_with_kis.sync_latest("005930")

        mock_kis_client.get_daily_prices.assert_called_once_with("005930", count=365)

    @pytest.mark.asyncio
    async def test_sync_latest_returns_zero_when_up_to_date(self, service_with_kis, mock_db, mock_kis_client):
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = yesterday
        mock_db.execute.return_value = mock_result

        result = await service_with_kis.sync_latest("005930")

        assert result == 0
        mock_kis_client.get_daily_prices.assert_not_called()
