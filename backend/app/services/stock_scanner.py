import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from app.services.kis_api import KISApiClient
from app.services.signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


class ScanType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class ScanResult:
    stock_code: str
    stock_name: str
    signal: str
    confidence: float
    current_price: float
    rsi: float
    volume_spike: bool
    reasoning: list[str]


class StockUniverse:
    KOSPI_STOCKS = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "000660", "name": "SK하이닉스"},
        {"code": "005380", "name": "현대차"},
        {"code": "005490", "name": "POSCO홀딩스"},
        {"code": "035420", "name": "NAVER"},
        {"code": "051910", "name": "LG화학"},
        {"code": "006400", "name": "삼성SDI"},
        {"code": "035720", "name": "카카오"},
        {"code": "028260", "name": "삼성물산"},
        {"code": "105560", "name": "KB금융"},
        {"code": "055550", "name": "신한지주"},
        {"code": "096770", "name": "SK이노베이션"},
        {"code": "003550", "name": "LG"},
        {"code": "017670", "name": "SK텔레콤"},
        {"code": "034730", "name": "SK"},
        {"code": "012330", "name": "현대모비스"},
        {"code": "066570", "name": "LG전자"},
        {"code": "003670", "name": "포스코퓨처엠"},
        {"code": "207940", "name": "삼성바이오로직스"},
        {"code": "000270", "name": "기아"},
    ]

    KOSDAQ_STOCKS = [
        {"code": "247540", "name": "에코프로비엠"},
        {"code": "086520", "name": "에코프로"},
        {"code": "373220", "name": "LG에너지솔루션"},
        {"code": "352820", "name": "하이브"},
        {"code": "068270", "name": "셀트리온"},
        {"code": "091990", "name": "셀트리온헬스케어"},
        {"code": "263750", "name": "펄어비스"},
        {"code": "293490", "name": "카카오게임즈"},
        {"code": "035900", "name": "JYP Ent."},
        {"code": "041510", "name": "에스엠"},
    ]

    def get_kospi_stocks(self) -> list[dict]:
        return self.KOSPI_STOCKS.copy()

    def get_kosdaq_stocks(self) -> list[dict]:
        return self.KOSDAQ_STOCKS.copy()

    def get_all_stocks(self) -> list[dict]:
        return self.KOSPI_STOCKS + self.KOSDAQ_STOCKS


class StockScanner:
    MAX_CONCURRENT_REQUESTS = 5
    MIN_DATA_POINTS = 30

    def __init__(
        self,
        kis_api: KISApiClient,
        signal_generator: SignalGenerator,
    ) -> None:
        self.kis_api = kis_api
        self.signal_generator = signal_generator
        self.universe = StockUniverse()

    async def scan_market(
        self,
        scan_type: ScanType = ScanType.BUY,
        min_confidence: float = 0.5,
        limit: int = 10,
        sector: str | None = None,
    ) -> list[ScanResult]:
        stocks = self.universe.get_all_stocks()

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        async def scan_stock(stock: dict) -> ScanResult | None:
            async with semaphore:
                return await self._analyze_stock(stock, scan_type, min_confidence)

        tasks = [scan_stock(stock) for stock in stocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[ScanResult] = []
        for result in results:
            if isinstance(result, ScanResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Scan error: {result}")

        valid_results.sort(key=lambda r: r.confidence, reverse=True)

        return valid_results[:limit]

    async def _analyze_stock(
        self,
        stock: dict,
        scan_type: ScanType,
        min_confidence: float,
    ) -> ScanResult | None:
        try:
            price_data = await self.kis_api.get_daily_prices(stock["code"], days=60)

            if not price_data or len(price_data) < self.MIN_DATA_POINTS:
                return None

            prices = [float(d.get("close", d.get("stck_clpr", 0))) for d in price_data]
            volumes = [float(d.get("volume", d.get("acml_vol", 0))) for d in price_data]

            prices = list(reversed(prices))
            volumes = list(reversed(volumes))

            signal = self.signal_generator.generate_signal(prices, volumes)

            signal_value = signal.signal.value.upper()
            if signal_value != scan_type.value:
                return None

            if signal.confidence < min_confidence:
                return None

            current_price = prices[-1] if prices else 0.0
            rsi = signal.indicators.get("rsi", 50.0)
            volume_spike = signal.indicators.get("volume_spike", False)

            reasoning = self._parse_reasoning(signal.reason)

            return ScanResult(
                stock_code=stock["code"],
                stock_name=stock["name"],
                signal=scan_type.value,
                confidence=signal.confidence,
                current_price=current_price,
                rsi=rsi,
                volume_spike=volume_spike,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.warning(f"Error analyzing {stock['code']}: {e}")
            return None

    def _parse_reasoning(self, reason: str) -> list[str]:
        if not reason:
            return []

        parts = reason.split(", ")
        return [part.strip() for part in parts if part.strip()]
