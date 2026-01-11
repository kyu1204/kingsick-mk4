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


@dataclass
class OrderStatusResult:
    """Order status inquiry result.

    Fields:
        order_id: Order number (ODNO)
        stock_code: Stock code (PDNO)
        stock_name: Stock name
        order_side: BUY or SELL
        order_quantity: Original order quantity
        filled_quantity: Total filled quantity
        filled_price: Average filled price
        order_status: Current order status
        order_time: Order time (HHMMSS)
        filled_time: Last fill time (HHMMSS or None)
    """

    order_id: str
    stock_code: str
    stock_name: str
    order_side: OrderSide
    order_quantity: int
    filled_quantity: int
    filled_price: float
    order_status: OrderStatus
    order_time: str
    filled_time: str | None


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

    # Rate limit error codes (초당 거래건수 초과)
    RATE_LIMIT_CODES = {"EGW00201"}

    # Maximum retry attempts for network errors
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    RATE_LIMIT_DELAY = 1.0  # seconds to wait on rate limit

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
            account_no: Account number (format: XXXXXXXX-XX or XXXXXXXXXX)
            is_mock: True for paper trading, False for real trading
        """
        self._app_key = app_key
        self._app_secret = app_secret
        self._account_no = self._normalize_account_no(account_no)
        self._is_mock = is_mock
        self._base_url = self.MOCK_BASE_URL if is_mock else self.REAL_BASE_URL
        self._access_token: str | None = None
        self._http_client = httpx.AsyncClient(timeout=30.0)

    @staticmethod
    def _normalize_account_no(account_no: str) -> str:
        """Normalize account number to XXXXXXXX-XX format."""
        account_no = account_no.replace("-", "").strip()
        if len(account_no) == 10:
            return f"{account_no[:8]}-{account_no[8:]}"
        return account_no

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

    def _is_rate_limited(self, response_data: dict) -> bool:  # type: ignore[type-arg]
        msg_cd = response_data.get("msg_cd", "")
        msg1 = response_data.get("msg1", "")
        return msg_cd in self.RATE_LIMIT_CODES or "초당 거래건수" in msg1

    async def authenticate(self) -> None:
        """Obtain OAuth access token.

        Raises:
            KISApiError: If authentication fails
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
                return

            self._access_token = None
            error_msg = (
                result.get("error_description")
                or result.get("msg1")
                or f"HTTP {response.status_code}"
            )
            raise KISApiError(f"Authentication failed: {error_msg}")
        except httpx.HTTPError as e:
            self._access_token = None
            raise KISApiError(f"Authentication network error: {e}") from e

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

        # Check for rate limit and retry
        for _ in range(self.MAX_RETRIES):
            if not self._is_rate_limited(data):
                break
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
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

        Uses the 국내주식기간별시세 API (FHKST03010100) which supports up to 100 days
        per request with date range specification. This is preferred over
        FHKST01010400 which only returns 30 days.

        Args:
            stock_code: Stock code
            count: Number of days to retrieve (default: 100, max: 100 per request)

        Returns:
            List of daily OHLCV data dictionaries (oldest first for technical analysis)

        Raises:
            KISApiError: On API error or if not authenticated
        """
        from datetime import datetime, timedelta

        self._ensure_authenticated()

        tr_id = "FHKST03010100"
        url = f"{self._base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = self._get_headers(tr_id)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=count + 50)

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
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

        # Check for rate limit and retry
        for _ in range(self.MAX_RETRIES):
            if not self._is_rate_limited(data):
                break
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
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

        # Check for rate limit and retry
        for _ in range(self.MAX_RETRIES):
            if not self._is_rate_limited(data):
                break
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
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

        # Check for rate limit and retry
        for _ in range(self.MAX_RETRIES):
            if not self._is_rate_limited(data):
                break
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
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

    async def get_order_status(self, order_id: str) -> OrderStatusResult | None:
        self._ensure_authenticated()

        tr_id = "VTTC8001R" if self._is_mock else "TTTC8001R"
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        headers = self._get_headers(tr_id)

        acnt_parts = self._account_no.split("-")
        cano = acnt_parts[0] if len(acnt_parts) > 0 else ""
        acnt_prdt_cd = acnt_parts[1] if len(acnt_parts) > 1 else "01"

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "INQR_STRT_DT": "",
            "INQR_END_DT": "",
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": order_id,
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = await self._request_with_retry("GET", url, headers=headers, params=params)
        data = response.json()

        if await self._check_and_refresh_token(data):
            headers = self._get_headers(tr_id)
            response = await self._request_with_retry("GET", url, headers=headers, params=params)
            data = response.json()

        if data.get("rt_cd") != "0":
            raise KISApiError(data.get("msg1", "Unknown API error"))

        output1 = data.get("output1", [])
        if not output1:
            return None

        order_data = None
        for item in output1:
            if item.get("odno") == order_id:
                order_data = item
                break

        if order_data is None:
            return None

        order_qty = int(order_data.get("ord_qty", 0))
        filled_qty = int(order_data.get("tot_ccld_qty", 0))

        if filled_qty == 0:
            status = OrderStatus.PENDING
        elif filled_qty >= order_qty:
            status = OrderStatus.FILLED
        else:
            status = OrderStatus.PARTIALLY_FILLED

        sll_buy_code = order_data.get("sll_buy_dvsn_cd", "02")
        order_side = OrderSide.SELL if sll_buy_code == "01" else OrderSide.BUY

        filled_time_raw = order_data.get("ccld_tmd", "")
        filled_time = filled_time_raw if filled_time_raw else None

        return OrderStatusResult(
            order_id=order_data.get("odno", order_id),
            stock_code=order_data.get("pdno", ""),
            stock_name=order_data.get("prdt_name", ""),
            order_side=order_side,
            order_quantity=order_qty,
            filled_quantity=filled_qty,
            filled_price=float(order_data.get("avg_prvs", 0)),
            order_status=status,
            order_time=order_data.get("ord_tmd", ""),
            filled_time=filled_time,
        )
