from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.stock_scanner import (
    ScanResult,
    ScanType,
    StockScanner,
    StockUniverse,
)


@dataclass
class MockPriceData:
    prices: list[float]
    volumes: list[float]


class TestScanResult:
    def test_create_scan_result(self):
        result = ScanResult(
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.78,
            current_price=72500.0,
            rsi=25.3,
            volume_spike=True,
            reasoning=["RSI 과매도", "거래량 급증"],
        )
        assert result.stock_code == "005930"
        assert result.signal == "BUY"
        assert result.confidence == 0.78


class TestStockUniverse:
    def test_get_kospi_stocks(self):
        universe = StockUniverse()
        stocks = universe.get_kospi_stocks()
        assert len(stocks) > 0
        assert all("code" in s and "name" in s for s in stocks)

    def test_get_kosdaq_stocks(self):
        universe = StockUniverse()
        stocks = universe.get_kosdaq_stocks()
        assert len(stocks) > 0
        assert all("code" in s and "name" in s for s in stocks)

    def test_get_all_stocks(self):
        universe = StockUniverse()
        stocks = universe.get_all_stocks()
        kospi = universe.get_kospi_stocks()
        kosdaq = universe.get_kosdaq_stocks()
        assert len(stocks) == len(kospi) + len(kosdaq)


class TestStockScanner:
    @pytest.fixture
    def mock_kis_api(self):
        mock = MagicMock()
        mock.get_daily_prices = AsyncMock(
            return_value=[
                {"close": 72500, "volume": 1000000},
                {"close": 72000, "volume": 900000},
                {"close": 71500, "volume": 800000},
            ]
            * 10
        )
        mock.get_current_price = AsyncMock(return_value={"price": 72500})
        return mock

    @pytest.fixture
    def mock_signal_generator(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def scanner(self, mock_kis_api, mock_signal_generator):
        return StockScanner(mock_kis_api, mock_signal_generator)

    @pytest.mark.asyncio
    async def test_scan_returns_buy_signals(self, scanner, mock_signal_generator):
        mock_signal_generator.generate_signal.return_value = MagicMock(
            signal=MagicMock(value="buy"),
            confidence=0.75,
            reason="RSI oversold",
            indicators={"rsi": 25.0, "volume_spike": True},
        )

        results = await scanner.scan_market(scan_type=ScanType.BUY, limit=5)

        assert len(results) <= 5
        for result in results:
            assert result.signal == "BUY"
            assert result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_scan_returns_sell_signals(self, scanner, mock_signal_generator):
        mock_signal_generator.generate_signal.return_value = MagicMock(
            signal=MagicMock(value="sell"),
            confidence=0.72,
            reason="RSI overbought",
            indicators={"rsi": 75.0, "volume_spike": False},
        )

        results = await scanner.scan_market(scan_type=ScanType.SELL, limit=5)

        assert len(results) <= 5
        for result in results:
            assert result.signal == "SELL"

    @pytest.mark.asyncio
    async def test_scan_filters_by_min_confidence(self, scanner, mock_signal_generator):
        call_count = 0

        def alternating_confidence(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return MagicMock(
                    signal=MagicMock(value="buy"),
                    confidence=0.8,
                    reason="Strong signal",
                    indicators={"rsi": 22.0, "volume_spike": True},
                )
            return MagicMock(
                signal=MagicMock(value="buy"),
                confidence=0.3,
                reason="Weak signal",
                indicators={"rsi": 40.0, "volume_spike": False},
            )

        mock_signal_generator.generate_signal.side_effect = alternating_confidence

        results = await scanner.scan_market(
            scan_type=ScanType.BUY, min_confidence=0.5, limit=50
        )

        for result in results:
            assert result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_scan_limits_results(self, scanner, mock_signal_generator):
        mock_signal_generator.generate_signal.return_value = MagicMock(
            signal=MagicMock(value="buy"),
            confidence=0.75,
            reason="RSI oversold",
            indicators={"rsi": 25.0, "volume_spike": True},
        )

        results = await scanner.scan_market(scan_type=ScanType.BUY, limit=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_scan_sorts_by_confidence_descending(
        self, scanner, mock_signal_generator
    ):
        confidences = [0.6, 0.9, 0.7, 0.8, 0.5]
        call_idx = 0

        def varying_confidence(*args, **kwargs):
            nonlocal call_idx
            conf = confidences[call_idx % len(confidences)]
            call_idx += 1
            return MagicMock(
                signal=MagicMock(value="buy"),
                confidence=conf,
                reason="Signal",
                indicators={"rsi": 25.0, "volume_spike": True},
            )

        mock_signal_generator.generate_signal.side_effect = varying_confidence

        results = await scanner.scan_market(
            scan_type=ScanType.BUY, min_confidence=0.5, limit=10
        )

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].confidence >= results[i + 1].confidence

    @pytest.mark.asyncio
    async def test_scan_handles_hold_signals(self, scanner, mock_signal_generator):
        mock_signal_generator.generate_signal.return_value = MagicMock(
            signal=MagicMock(value="hold"),
            confidence=0.0,
            reason="No signal",
            indicators={"rsi": 50.0, "volume_spike": False},
        )

        results = await scanner.scan_market(scan_type=ScanType.BUY, limit=10)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_scan_handles_api_error_gracefully(
        self, scanner, mock_kis_api, mock_signal_generator
    ):
        mock_kis_api.get_daily_prices.side_effect = Exception("API Error")

        results = await scanner.scan_market(scan_type=ScanType.BUY, limit=10)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_scan_includes_reasoning(self, scanner, mock_signal_generator):
        mock_signal_generator.generate_signal.return_value = MagicMock(
            signal=MagicMock(value="buy"),
            confidence=0.75,
            reason="RSI oversold (25.0), Volume spike detected",
            indicators={"rsi": 25.0, "volume_spike": True},
        )

        results = await scanner.scan_market(scan_type=ScanType.BUY, limit=5)

        if results:
            assert len(results[0].reasoning) > 0


class TestScanType:
    def test_scan_type_values(self):
        assert ScanType.BUY.value == "BUY"
        assert ScanType.SELL.value == "SELL"
