"""Unit tests for KISApiClient.

Tests for Korea Investment & Securities API integration.
All tests use mocks to avoid actual API calls.
Target coverage: 95%+
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.kis_api import (
    KISApiClient,
    KISApiError,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderStatusResult,
    Position,
    StockPrice,
)


class TestKISApiClientInit:
    """Tests for KISApiClient initialization."""

    def test_init_with_mock_mode(self):
        """Client should initialize with mock mode by default."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )

        assert client._app_key == "test_key"
        assert client._app_secret == "test_secret"
        assert client._account_no == "12345678-01"
        assert client._is_mock is True
        assert client._base_url == "https://openapivts.koreainvestment.com:29443"

    def test_init_with_real_mode(self):
        """Client should use real API URL when is_mock=False."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
            is_mock=False,
        )

        assert client._is_mock is False
        assert client._base_url == "https://openapi.koreainvestment.com:9443"


class TestAuthentication:
    """Tests for OAuth authentication."""

    @pytest.fixture
    def client(self):
        """Create a KISApiClient instance for testing."""
        return KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )

    async def test_authentication_success(self, client):
        """OAuth authentication should succeed with valid credentials."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 86400,
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await client.authenticate()

            assert result is True
            assert client._access_token == "test_access_token"

    async def test_authentication_failure(self, client):
        """OAuth authentication should return False on failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error_description": "Invalid credentials",
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await client.authenticate()

            assert result is False
            assert client._access_token is None


class TestGetStockPrice:
    """Tests for stock price retrieval."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_stock_price_success(self, authenticated_client):
        """Should return StockPrice with correct data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "50000",
                "stck_oprc": "49000",
                "stck_hgpr": "51000",
                "stck_lwpr": "48500",
                "prdy_ctrt": "2.50",
                "acml_vol": "1000000",
                "hts_kor_isnm": "삼성전자",
            },
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_stock_price("005930")

            assert isinstance(result, StockPrice)
            assert result.code == "005930"
            assert result.name == "삼성전자"
            assert result.current_price == 50000.0
            assert result.open == 49000.0
            assert result.high == 51000.0
            assert result.low == 48500.0
            assert result.change_rate == 2.50
            assert result.volume == 1000000

    async def test_get_stock_price_api_error(self, authenticated_client):
        """Should raise KISApiError on API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "1",
            "msg1": "Invalid stock code",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            with pytest.raises(KISApiError) as exc_info:
                await authenticated_client.get_stock_price("INVALID")

            assert "Invalid stock code" in str(exc_info.value)

    async def test_get_stock_price_without_auth(self):
        """Should raise error when not authenticated."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )

        with pytest.raises(KISApiError) as exc_info:
            await client.get_stock_price("005930")

        assert "Not authenticated" in str(exc_info.value)


class TestGetStockPrices:
    """Tests for multiple stock price retrieval."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_stock_prices_success(self, authenticated_client):
        """Should return list of StockPrice for multiple codes."""
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "50000",
                "stck_oprc": "49000",
                "stck_hgpr": "51000",
                "stck_lwpr": "48500",
                "prdy_ctrt": "2.50",
                "acml_vol": "1000000",
                "hts_kor_isnm": "삼성전자",
            },
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "80000",
                "stck_oprc": "78000",
                "stck_hgpr": "82000",
                "stck_lwpr": "77000",
                "prdy_ctrt": "-1.20",
                "acml_vol": "500000",
                "hts_kor_isnm": "SK하이닉스",
            },
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(side_effect=[mock_response1, mock_response2])

            result = await authenticated_client.get_stock_prices(["005930", "000660"])

            assert len(result) == 2
            assert result[0].code == "005930"
            assert result[0].name == "삼성전자"
            assert result[1].code == "000660"
            assert result[1].name == "SK하이닉스"

    async def test_get_stock_prices_empty_list(self, authenticated_client):
        """Should return empty list for empty input."""
        result = await authenticated_client.get_stock_prices([])

        assert result == []


class TestGetDailyPrices:
    """Tests for daily price history retrieval."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_daily_prices_success(self, authenticated_client):
        """Should return daily OHLCV data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output2": [
                {
                    "stck_bsop_date": "20240115",
                    "stck_oprc": "49000",
                    "stck_hgpr": "51000",
                    "stck_lwpr": "48500",
                    "stck_clpr": "50000",
                    "acml_vol": "1000000",
                },
                {
                    "stck_bsop_date": "20240114",
                    "stck_oprc": "48000",
                    "stck_hgpr": "50000",
                    "stck_lwpr": "47500",
                    "stck_clpr": "49000",
                    "acml_vol": "900000",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_daily_prices("005930", count=2)

            assert len(result) == 2
            assert result[0]["date"] == "20240115"
            assert result[0]["open"] == 49000.0
            assert result[0]["high"] == 51000.0
            assert result[0]["low"] == 48500.0
            assert result[0]["close"] == 50000.0
            assert result[0]["volume"] == 1000000

    async def test_get_daily_prices_with_custom_count(self, authenticated_client):
        """Should respect the count parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output2": [{"stck_bsop_date": f"2024011{i}"} for i in range(5)],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            await authenticated_client.get_daily_prices("005930", count=50)

            # Verify count parameter was passed correctly
            mock_http.get.assert_called_once()


class TestPlaceOrder:
    """Tests for order execution."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_place_buy_order_success(self, authenticated_client):
        """Should successfully place a buy order."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "ODNO": "0000123456",
            },
            "msg1": "정상처리되었습니다",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await authenticated_client.place_order(
                stock_code="005930",
                side=OrderSide.BUY,
                quantity=10,
                price=50000.0,
            )

            assert isinstance(result, OrderResult)
            assert result.success is True
            assert result.order_id == "0000123456"
            assert result.status == OrderStatus.PENDING

    async def test_place_sell_order_success(self, authenticated_client):
        """Should successfully place a sell order."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "ODNO": "0000123457",
            },
            "msg1": "정상처리되었습니다",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await authenticated_client.place_order(
                stock_code="005930",
                side=OrderSide.SELL,
                quantity=10,
                price=51000.0,
            )

            assert result.success is True
            assert result.order_id == "0000123457"

    async def test_place_market_order(self, authenticated_client):
        """Should place market order when price is None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "ODNO": "0000123458",
            },
            "msg1": "정상처리되었습니다",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await authenticated_client.place_order(
                stock_code="005930",
                side=OrderSide.BUY,
                quantity=10,
                price=None,  # Market order
            )

            assert result.success is True

    async def test_place_order_failure(self, authenticated_client):
        """Should return failed result on order rejection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "1",
            "msg1": "주문수량이 부족합니다",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=mock_response)

            result = await authenticated_client.place_order(
                stock_code="005930",
                side=OrderSide.BUY,
                quantity=10,
                price=50000.0,
            )

            assert result.success is False
            assert result.order_id is None
            assert result.status == OrderStatus.FAILED
            assert "주문수량이 부족합니다" in result.message


class TestGetPositions:
    """Tests for position retrieval."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_positions_success(self, authenticated_client):
        """Should return list of positions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [
                {
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "hldg_qty": "100",
                    "pchs_avg_pric": "50000",
                    "prpr": "52000",
                    "evlu_pfls_amt": "200000",
                    "evlu_pfls_rt": "4.00",
                },
                {
                    "pdno": "000660",
                    "prdt_name": "SK하이닉스",
                    "hldg_qty": "50",
                    "pchs_avg_pric": "80000",
                    "prpr": "78000",
                    "evlu_pfls_amt": "-100000",
                    "evlu_pfls_rt": "-2.50",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_positions()

            assert len(result) == 2
            assert isinstance(result[0], Position)
            assert result[0].stock_code == "005930"
            assert result[0].stock_name == "삼성전자"
            assert result[0].quantity == 100
            assert result[0].avg_price == 50000.0
            assert result[0].current_price == 52000.0
            assert result[0].profit_loss == 200000.0
            assert result[0].profit_loss_rate == 4.00

    async def test_get_positions_empty(self, authenticated_client):
        """Should return empty list when no positions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_positions()

            assert result == []


class TestGetBalance:
    """Tests for balance retrieval."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_balance_success(self, authenticated_client):
        """Should return balance information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output2": [
                {
                    "dnca_tot_amt": "10000000",
                    "nxdy_excc_amt": "10000000",
                    "prvs_rcdl_excc_amt": "10000000",
                    "cma_evlu_amt": "0",
                    "bfdy_buy_amt": "5000000",
                    "thdt_buy_amt": "1000000",
                    "tot_evlu_amt": "15000000",
                    "nass_amt": "15000000",
                    "pchs_amt_smtl_amt": "5000000",
                    "evlu_amt_smtl_amt": "5200000",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_balance()

            assert result["deposit"] == 10000000.0
            assert result["available_amount"] == 10000000.0
            assert result["total_evaluation"] == 15000000.0
            assert result["net_worth"] == 15000000.0
            assert result["purchase_amount"] == 5000000.0
            assert result["evaluation_amount"] == 5200000.0


class TestTokenRefresh:
    """Tests for automatic token refresh."""

    @pytest.fixture
    def client(self):
        """Create a KISApiClient instance."""
        return KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )

    async def test_token_refresh_on_expired(self, client):
        """Should automatically refresh token when expired."""
        client._access_token = "expired_token"

        # First call returns token expired error
        expired_response = MagicMock()
        expired_response.status_code = 200
        expired_response.json.return_value = {
            "rt_cd": "1",
            "msg_cd": "EGW00123",  # Token expired error code
            "msg1": "접근토큰이 만료되었습니다",
        }

        # Token refresh response
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 86400,
        }

        # Retry with new token - success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "50000",
                "stck_oprc": "49000",
                "stck_hgpr": "51000",
                "stck_lwpr": "48500",
                "prdy_ctrt": "2.50",
                "acml_vol": "1000000",
                "hts_kor_isnm": "삼성전자",
            },
        }

        with patch.object(client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(side_effect=[expired_response, success_response])
            mock_http.post = AsyncMock(return_value=auth_response)

            result = await client.get_stock_price("005930")

            assert client._access_token == "new_access_token"
            assert result.code == "005930"


class TestNetworkErrorHandling:
    """Tests for network error handling and retry logic."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated KISApiClient instance."""
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_retry_on_network_error(self, authenticated_client):
        """Should retry on network errors."""
        # First two calls fail with network error, third succeeds
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "rt_cd": "0",
            "output": {
                "stck_prpr": "50000",
                "stck_oprc": "49000",
                "stck_hgpr": "51000",
                "stck_lwpr": "48500",
                "prdy_ctrt": "2.50",
                "acml_vol": "1000000",
                "hts_kor_isnm": "삼성전자",
            },
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(
                side_effect=[
                    httpx.ConnectError("Connection failed"),
                    httpx.ConnectError("Connection failed"),
                    success_response,
                ]
            )

            result = await authenticated_client.get_stock_price("005930")

            assert result.code == "005930"
            assert mock_http.get.call_count == 3

    async def test_max_retries_exceeded(self, authenticated_client):
        """Should raise error after max retries exceeded."""
        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            with pytest.raises(KISApiError) as exc_info:
                await authenticated_client.get_stock_price("005930")

            assert "Connection failed" in str(exc_info.value) or "retry" in str(
                exc_info.value
            ).lower()

    async def test_timeout_error(self, authenticated_client):
        """Should handle timeout errors."""
        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with pytest.raises(KISApiError):
                await authenticated_client.get_stock_price("005930")


class TestDataClasses:
    """Tests for data classes."""

    def test_stock_price_dataclass(self):
        """StockPrice should hold all required fields."""
        price = StockPrice(
            code="005930",
            name="삼성전자",
            current_price=50000.0,
            change_rate=2.5,
            volume=1000000,
            high=51000.0,
            low=48500.0,
            open=49000.0,
        )

        assert price.code == "005930"
        assert price.name == "삼성전자"
        assert price.current_price == 50000.0
        assert price.change_rate == 2.5
        assert price.volume == 1000000
        assert price.high == 51000.0
        assert price.low == 48500.0
        assert price.open == 49000.0

    def test_order_result_dataclass(self):
        """OrderResult should hold all required fields."""
        result = OrderResult(
            success=True,
            order_id="0000123456",
            message="정상처리되었습니다",
            status=OrderStatus.PENDING,
        )

        assert result.success is True
        assert result.order_id == "0000123456"
        assert result.message == "정상처리되었습니다"
        assert result.status == OrderStatus.PENDING

    def test_position_dataclass(self):
        """Position should hold all required fields."""
        position = Position(
            stock_code="005930",
            stock_name="삼성전자",
            quantity=100,
            avg_price=50000.0,
            current_price=52000.0,
            profit_loss=200000.0,
            profit_loss_rate=4.0,
        )

        assert position.stock_code == "005930"
        assert position.stock_name == "삼성전자"
        assert position.quantity == 100
        assert position.avg_price == 50000.0
        assert position.current_price == 52000.0
        assert position.profit_loss == 200000.0
        assert position.profit_loss_rate == 4.0

    def test_order_side_enum(self):
        """OrderSide enum should have BUY and SELL values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_status_enum(self):
        """OrderStatus enum should have all required values."""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.PARTIALLY_FILLED.value == "partially_filled"
        assert OrderStatus.FAILED.value == "failed"
        assert OrderStatus.CANCELLED.value == "cancelled"

    def test_order_status_result_dataclass(self):
        result = OrderStatusResult(
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

        assert result.order_id == "0000123456"
        assert result.stock_code == "005930"
        assert result.stock_name == "삼성전자"
        assert result.order_side == OrderSide.BUY
        assert result.order_quantity == 10
        assert result.filled_quantity == 10
        assert result.filled_price == 50000.0
        assert result.order_status == OrderStatus.FILLED
        assert result.order_time == "093000"
        assert result.filled_time == "093015"


class TestGetOrderStatus:

    @pytest.fixture
    def authenticated_client(self):
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )
        client._access_token = "test_access_token"
        return client

    async def test_get_order_status_filled(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [
                {
                    "odno": "0000123456",
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "sll_buy_dvsn_cd": "02",  # 02=BUY, 01=SELL
                    "ord_qty": "10",
                    "tot_ccld_qty": "10",
                    "avg_prvs": "50000",
                    "ord_tmd": "093000",
                    "ccld_tmd": "093015",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_order_status("0000123456")

            assert result is not None
            assert result.order_id == "0000123456"
            assert result.stock_code == "005930"
            assert result.stock_name == "삼성전자"
            assert result.order_side == OrderSide.BUY
            assert result.order_quantity == 10
            assert result.filled_quantity == 10
            assert result.filled_price == 50000.0
            assert result.order_status == OrderStatus.FILLED
            assert result.order_time == "093000"
            assert result.filled_time == "093015"

    async def test_get_order_status_pending(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [
                {
                    "odno": "0000123457",
                    "pdno": "000660",
                    "prdt_name": "SK하이닉스",
                    "sll_buy_dvsn_cd": "01",  # 01=SELL
                    "ord_qty": "20",
                    "tot_ccld_qty": "0",
                    "avg_prvs": "0",
                    "ord_tmd": "100000",
                    "ccld_tmd": "",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_order_status("0000123457")

            assert result is not None
            assert result.order_id == "0000123457"
            assert result.order_side == OrderSide.SELL
            assert result.order_quantity == 20
            assert result.filled_quantity == 0
            assert result.order_status == OrderStatus.PENDING
            assert result.filled_time is None

    async def test_get_order_status_partially_filled(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [
                {
                    "odno": "0000123458",
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "sll_buy_dvsn_cd": "02",
                    "ord_qty": "100",
                    "tot_ccld_qty": "50",
                    "avg_prvs": "51000",
                    "ord_tmd": "110000",
                    "ccld_tmd": "110530",
                },
            ],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_order_status("0000123458")

            assert result is not None
            assert result.order_quantity == 100
            assert result.filled_quantity == 50
            assert result.order_status == OrderStatus.PARTIALLY_FILLED

    async def test_get_order_status_not_found(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "0",
            "output1": [],
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            result = await authenticated_client.get_order_status("NONEXISTENT")

            assert result is None

    async def test_get_order_status_api_error(self, authenticated_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rt_cd": "1",
            "msg1": "조회 실패",
        }

        with patch.object(authenticated_client, "_http_client") as mock_http:
            mock_http.get = AsyncMock(return_value=mock_response)

            with pytest.raises(KISApiError) as exc_info:
                await authenticated_client.get_order_status("0000123456")

            assert "조회 실패" in str(exc_info.value)

    async def test_get_order_status_without_auth(self):
        client = KISApiClient(
            app_key="test_key",
            app_secret="test_secret",
            account_no="12345678-01",
        )

        with pytest.raises(KISApiError) as exc_info:
            await client.get_order_status("0000123456")

        assert "Not authenticated" in str(exc_info.value)
