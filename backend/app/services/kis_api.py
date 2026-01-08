"""Korea Investment & Securities API Client.

This module provides async API integration with Korea Investment & Securities
REST API for stock price queries, order execution, and balance inquiries.
Supports both mock (paper trading) and real trading modes.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx


class OrderSide(Enum):
    """Order side enum."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status enum."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StockPrice:
    """Stock price data."""

    code: str
    name: str
    current_price: float
    change_rate: float
    volume: int
    high: float
    low: float
    open: float


@dataclass
class OrderResult:
    """Order execution result."""

    success: bool
    order_id: str | None
    message: str
    status: OrderStatus


@dataclass
class Position:
    """Stock position data."""

    stock_code: str
    stock_name: str
    quantity: int
    avg_price: float
    current_price: float
    profit_loss: float
    profit_loss_rate: float


class KISApiError(Exception):
    """Exception raised for KIS API errors."""

    pass


class KISApiClient:
    """Korea Investment & Securities API Client.

    Provides async methods for interacting with the KIS REST API:
    - OAuth token management with automatic refresh
    - Stock price queries (current and historical)
    - Order placement (market and limit orders)
    - Position and balance inquiries

    Args:
        app_key: API app key
        app_secret: API app secret
        account_no: Account number (format: XXXXXXXX-XX)
        is_mock: True for paper trading, False for real trading
    """

    # API base URLs
    MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
    REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"

    # Token expired error codes
    TOKEN_EXPIRED_CODES = {"EGW00123", "EGW00121"}

    # Maximum retry attempts for network errors
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        account_no: str,
        is_mock: bool = True,
    ):
        """Initialize KIS API client.

        Args:
            app_key: API app key
            app_secret: API app secret
            account_no: Account number (format: XXXXXXXX-XX)
            is_mock: True for paper trading, False for real trading
        """
        self._app_key = app_key
        self._app_secret = app_secret
        self._account_no = account_no
        self._is_mock = is_mock
        self._base_url = self.MOCK_BASE_URL if is_mock else self.REAL_BASE_URL
        self._access_token: str | None = None
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "KISApiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()

    def _get_headers(self, tr_id: str) -> dict[str, str]:
        """Build common headers for API requests.

        Args:
            tr_id: Transaction ID for the request

        Returns:
            Headers dictionary
        """
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._access_token}",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "tr_id": tr_id,
        }

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET or POST)
            url: Request URL
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            KISApiError: On persistent network errors
        """
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if method == "GET":
                    return await self._http_client.get(url, **kwargs)
                else:
                    return await self._http_client.post(url, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)

        raise KISApiError(f"Network error after {self.MAX_RETRIES} retries: {last_error}")

    async def _check_and_refresh_token(
        self,
        response_data: dict,  # type: ignore[type-arg]
    ) -> bool:
        """Check if token is expired and refresh if needed.

        Args:
            response_data: API response data

        Returns:
            True if token was refreshed, False otherwise
        """
        msg_cd = response_data.get("msg_cd", "")
        if msg_cd in self.TOKEN_EXPIRED_CODES:
            await self.authenticate()
            return True
        return False

    async def authenticate(self) -> bool:
        """Obtain OAuth access token.

        Returns:
            True if authentication successful, False otherwise
        """
        url = f"{self._base_url}/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
        }

        try:
            response = await self._http_client.post(url, json=data)
            result = response.json()

            if response.status_code == 200 and "access_token" in result:
                self._access_token = result["access_token"]
                return True
            else:
                self._access_token = None
                return False
        except Exception:
            self._access_token = None
            return False

    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated.

        Raises:
            KISApiError: If not authenticated
        """
        if not self._access_token:
            raise KISApiError("Not authenticated. Call authenticate() first.")

    async def get_stock_price(self, stock_code: str) -> StockPrice:
        """Get current stock price.

        Args:
            stock_code: Stock code (e.g., "005930" for Samsung Electronics)

        Returns:
            StockPrice with current market data

        Raises:
            KISApiError: On API error or if not authenticated
        """
        self._ensure_authenticated()

        tr_id = "FHKST01010100"
        url = f"{self._base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        response = await self._request_with_retry("GET", url, headers=headers, params=params)
        data = response.json()

        # Check for token expiration and retry
        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("GET", url, headers=headers, params=params)
            data = response.json()

        if data.get("rt_cd") != "0":
            raise KISApiError(data.get("msg1", "Unknown API error"))

        output = data["output"]
        return StockPrice(
            code=stock_code,
            name=output.get("hts_kor_isnm", ""),
            current_price=float(output.get("stck_prpr", 0)),
            open=float(output.get("stck_oprc", 0)),
            high=float(output.get("stck_hgpr", 0)),
            low=float(output.get("stck_lwpr", 0)),
            change_rate=float(output.get("prdy_ctrt", 0)),
            volume=int(output.get("acml_vol", 0)),
        )

    async def get_stock_prices(self, stock_codes: list[str]) -> list[StockPrice]:
        """Get current prices for multiple stocks.

        Args:
            stock_codes: List of stock codes

        Returns:
            List of StockPrice objects
        """
        if not stock_codes:
            return []

        results: list[StockPrice] = []
        for code in stock_codes:
            price = await self.get_stock_price(code)
            results.append(price)

        return results

    async def get_daily_prices(
        self,
        stock_code: str,
        count: int = 100,
    ) -> list[dict[str, float | int | str]]:
        """Get daily OHLCV data for technical analysis.

        Args:
            stock_code: Stock code
            count: Number of days to retrieve (default: 100)

        Returns:
            List of daily OHLCV data dictionaries

        Raises:
            KISApiError: On API error or if not authenticated
        """
        self._ensure_authenticated()

        tr_id = "FHKST01010400"
        url = f"{self._base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        }

        response = await self._request_with_retry("GET", url, headers=headers, params=params)
        data = response.json()

        # Check for token expiration and retry
        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("GET", url, headers=headers, params=params)
            data = response.json()

        if data.get("rt_cd") != "0":
            raise KISApiError(data.get("msg1", "Unknown API error"))

        output = data.get("output2", [])
        results: list[dict[str, float | int | str]] = []

        for item in output[:count]:
            results.append(
                {
                    "date": item.get("stck_bsop_date", ""),
                    "open": float(item.get("stck_oprc", 0)),
                    "high": float(item.get("stck_hgpr", 0)),
                    "low": float(item.get("stck_lwpr", 0)),
                    "close": float(item.get("stck_clpr", 0)),
                    "volume": int(item.get("acml_vol", 0)),
                }
            )

        return results

    async def place_order(
        self,
        stock_code: str,
        side: OrderSide,
        quantity: int,
        price: float | None = None,
    ) -> OrderResult:
        """Place a stock order.

        Args:
            stock_code: Stock code
            side: BUY or SELL
            quantity: Number of shares
            price: Limit price (None for market order)

        Returns:
            OrderResult with execution status

        Raises:
            KISApiError: On API error or if not authenticated
        """
        self._ensure_authenticated()

        # Transaction ID varies by mock/real and buy/sell
        if self._is_mock:
            tr_id = "VTTC0802U" if side == OrderSide.BUY else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side == OrderSide.BUY else "TTTC0801U"

        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers(tr_id)

        # Account number split
        acnt_parts = self._account_no.split("-")
        cano = acnt_parts[0] if len(acnt_parts) > 0 else ""
        acnt_prdt_cd = acnt_parts[1] if len(acnt_parts) > 1 else "01"

        # Order type: 00 for limit, 01 for market
        ord_dvsn = "00" if price else "01"
        ord_unpr = str(int(price)) if price else "0"

        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": ord_unpr,
        }

        response = await self._request_with_retry("POST", url, headers=headers, json=body)
        data = response.json()

        # Check for token expiration and retry
        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("POST", url, headers=headers, json=body)
            data = response.json()

        if data.get("rt_cd") == "0":
            return OrderResult(
                success=True,
                order_id=data.get("output", {}).get("ODNO"),
                message=data.get("msg1", "Order placed successfully"),
                status=OrderStatus.PENDING,
            )
        else:
            return OrderResult(
                success=False,
                order_id=None,
                message=data.get("msg1", "Order failed"),
                status=OrderStatus.FAILED,
            )

    async def get_positions(self) -> list[Position]:
        """Get current stock positions.

        Returns:
            List of Position objects

        Raises:
            KISApiError: On API error or if not authenticated
        """
        self._ensure_authenticated()

        tr_id = "VTTC8434R" if self._is_mock else "TTTC8434R"
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers(tr_id)

        acnt_parts = self._account_no.split("-")
        cano = acnt_parts[0] if len(acnt_parts) > 0 else ""
        acnt_prdt_cd = acnt_parts[1] if len(acnt_parts) > 1 else "01"

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = await self._request_with_retry("GET", url, headers=headers, params=params)
        data = response.json()

        # Check for token expiration and retry
        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("GET", url, headers=headers, params=params)
            data = response.json()

        if data.get("rt_cd") != "0":
            raise KISApiError(data.get("msg1", "Unknown API error"))

        positions: list[Position] = []
        for item in data.get("output1", []):
            positions.append(
                Position(
                    stock_code=item.get("pdno", ""),
                    stock_name=item.get("prdt_name", ""),
                    quantity=int(item.get("hldg_qty", 0)),
                    avg_price=float(item.get("pchs_avg_pric", 0)),
                    current_price=float(item.get("prpr", 0)),
                    profit_loss=float(item.get("evlu_pfls_amt", 0)),
                    profit_loss_rate=float(item.get("evlu_pfls_rt", 0)),
                )
            )

        return positions

    async def get_balance(self) -> dict[str, float]:
        """Get account balance information.

        Returns:
            Dictionary with balance information:
                - deposit: Total deposit amount
                - available_amount: Available amount for trading
                - total_evaluation: Total portfolio evaluation
                - net_worth: Net asset value
                - purchase_amount: Total purchase amount
                - evaluation_amount: Total stock evaluation amount

        Raises:
            KISApiError: On API error or if not authenticated
        """
        self._ensure_authenticated()

        tr_id = "VTTC8434R" if self._is_mock else "TTTC8434R"
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers(tr_id)

        acnt_parts = self._account_no.split("-")
        cano = acnt_parts[0] if len(acnt_parts) > 0 else ""
        acnt_prdt_cd = acnt_parts[1] if len(acnt_parts) > 1 else "01"

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = await self._request_with_retry("GET", url, headers=headers, params=params)
        data = response.json()

        # Check for token expiration and retry
        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("GET", url, headers=headers, params=params)
            data = response.json()

        if data.get("rt_cd") != "0":
            raise KISApiError(data.get("msg1", "Unknown API error"))

        output2 = data.get("output2", [{}])
        balance_data = output2[0] if output2 else {}

        return {
            "deposit": float(balance_data.get("dnca_tot_amt", 0)),
            "available_amount": float(balance_data.get("nxdy_excc_amt", 0)),
            "total_evaluation": float(balance_data.get("tot_evlu_amt", 0)),
            "net_worth": float(balance_data.get("nass_amt", 0)),
            "purchase_amount": float(balance_data.get("pchs_amt_smtl_amt", 0)),
            "evaluation_amount": float(balance_data.get("evlu_amt_smtl_amt", 0)),
        }
