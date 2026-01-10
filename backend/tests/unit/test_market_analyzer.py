"""Unit tests for MarketAnalyzer service."""

import math
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.market_analyzer import (
    InsufficientDataError,
    MarketAnalyzer,
    MarketIndicators,
    MarketSentiment,
    MarketState,
    MarketTrend,
)


class TestMarketTrendClassification:
    """Test trend classification logic."""

    def test_uptrend_values(self):
        assert MarketTrend.UPTREND.value == "UPTREND"
        assert MarketTrend.DOWNTREND.value == "DOWNTREND"
        assert MarketTrend.SIDEWAYS.value == "SIDEWAYS"

    def test_sentiment_values(self):
        assert MarketSentiment.EXTREME_FEAR.value == "EXTREME_FEAR"
        assert MarketSentiment.FEAR.value == "FEAR"
        assert MarketSentiment.NEUTRAL.value == "NEUTRAL"
        assert MarketSentiment.GREED.value == "GREED"
        assert MarketSentiment.EXTREME_GREED.value == "EXTREME_GREED"


class TestMarketIndicators:
    """Test MarketIndicators dataclass."""

    def test_create_with_all_values(self):
        indicators = MarketIndicators(
            rsi_14=45.5,
            ma_5=100.0,
            ma_20=98.0,
            ma_60=95.0,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            volume_ratio=1.2,
        )
        assert indicators.rsi_14 == 45.5
        assert indicators.ma_5 == 100.0
        assert indicators.volume_ratio == 1.2

    def test_create_with_none_values(self):
        indicators = MarketIndicators(
            rsi_14=None,
            ma_5=None,
            ma_20=None,
            ma_60=None,
            macd=None,
            macd_signal=None,
            macd_histogram=None,
            volume_ratio=None,
        )
        assert indicators.rsi_14 is None
        assert indicators.ma_5 is None


class TestMarketAnalyzerHelpers:
    """Test helper methods of MarketAnalyzer."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    def test_get_last_valid_with_valid_values(self, analyzer):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = analyzer._get_last_valid(values)
        assert result == 5.0

    def test_get_last_valid_with_nan_at_end(self, analyzer):
        values = [1.0, 2.0, math.nan]
        result = analyzer._get_last_valid(values)
        assert result is None

    def test_get_last_valid_with_empty_list(self, analyzer):
        result = analyzer._get_last_valid([])
        assert result is None

    def test_classify_sentiment_extreme_fear(self, analyzer):
        assert analyzer._classify_sentiment(10) == MarketSentiment.EXTREME_FEAR
        assert analyzer._classify_sentiment(0) == MarketSentiment.EXTREME_FEAR
        assert analyzer._classify_sentiment(20) == MarketSentiment.EXTREME_FEAR

    def test_classify_sentiment_fear(self, analyzer):
        assert analyzer._classify_sentiment(21) == MarketSentiment.FEAR
        assert analyzer._classify_sentiment(30) == MarketSentiment.FEAR
        assert analyzer._classify_sentiment(40) == MarketSentiment.FEAR

    def test_classify_sentiment_neutral(self, analyzer):
        assert analyzer._classify_sentiment(41) == MarketSentiment.NEUTRAL
        assert analyzer._classify_sentiment(50) == MarketSentiment.NEUTRAL
        assert analyzer._classify_sentiment(60) == MarketSentiment.NEUTRAL

    def test_classify_sentiment_greed(self, analyzer):
        assert analyzer._classify_sentiment(61) == MarketSentiment.GREED
        assert analyzer._classify_sentiment(70) == MarketSentiment.GREED
        assert analyzer._classify_sentiment(80) == MarketSentiment.GREED

    def test_classify_sentiment_extreme_greed(self, analyzer):
        assert analyzer._classify_sentiment(81) == MarketSentiment.EXTREME_GREED
        assert analyzer._classify_sentiment(90) == MarketSentiment.EXTREME_GREED
        assert analyzer._classify_sentiment(100) == MarketSentiment.EXTREME_GREED


class TestDetermineTrend:
    """Test trend determination logic."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    def test_strong_uptrend(self, analyzer):
        prices = [95.0, 96.0, 97.0, 98.0, 99.0, 100.0]
        indicators = MarketIndicators(
            rsi_14=65.0,
            ma_5=99.0,
            ma_20=97.0,
            ma_60=94.0,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            volume_ratio=1.2,
        )
        trend = analyzer._determine_trend(prices, indicators)
        assert trend == MarketTrend.UPTREND

    def test_strong_downtrend(self, analyzer):
        prices = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0]
        indicators = MarketIndicators(
            rsi_14=35.0,
            ma_5=101.0,
            ma_20=103.0,
            ma_60=106.0,
            macd=-0.5,
            macd_signal=-0.3,
            macd_histogram=-0.2,
            volume_ratio=0.8,
        )
        trend = analyzer._determine_trend(prices, indicators)
        assert trend == MarketTrend.DOWNTREND

    def test_sideways_trend(self, analyzer):
        prices = [100.0, 101.0, 99.0, 100.0, 101.0, 100.0]
        indicators = MarketIndicators(
            rsi_14=50.0,
            ma_5=100.0,
            ma_20=100.0,
            ma_60=100.0,
            macd=0.0,
            macd_signal=0.0,
            macd_histogram=0.0,
            volume_ratio=1.0,
        )
        trend = analyzer._determine_trend(prices, indicators)
        assert trend == MarketTrend.SIDEWAYS

    def test_trend_with_missing_indicators(self, analyzer):
        prices = [100.0]
        indicators = MarketIndicators(
            rsi_14=None,
            ma_5=None,
            ma_20=None,
            ma_60=None,
            macd=None,
            macd_signal=None,
            macd_histogram=None,
            volume_ratio=None,
        )
        trend = analyzer._determine_trend(prices, indicators)
        assert trend == MarketTrend.SIDEWAYS


class TestCalculateFearGreed:
    """Test Fear-Greed index calculation."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    def test_neutral_conditions(self, analyzer):
        prices = [100.0] * 30
        volumes = [1000.0] * 30
        indicators = MarketIndicators(
            rsi_14=50.0,
            ma_5=100.0,
            ma_20=100.0,
            ma_60=100.0,
            macd=0.0,
            macd_signal=0.0,
            macd_histogram=0.0,
            volume_ratio=1.0,
        )
        fg = analyzer._calculate_fear_greed(prices, volumes, indicators)
        assert 40 <= fg <= 60

    def test_high_fear_conditions(self, analyzer):
        prices = [90.0] * 30
        volumes = [500.0] * 30
        indicators = MarketIndicators(
            rsi_14=20.0,
            ma_5=92.0,
            ma_20=100.0,
            ma_60=105.0,
            macd=-0.5,
            macd_signal=-0.3,
            macd_histogram=-0.2,
            volume_ratio=0.5,
        )
        fg = analyzer._calculate_fear_greed(prices, volumes, indicators)
        assert fg < 50

    def test_high_greed_conditions(self, analyzer):
        prices = [110.0] * 30
        volumes = [2000.0] * 30
        indicators = MarketIndicators(
            rsi_14=80.0,
            ma_5=108.0,
            ma_20=100.0,
            ma_60=95.0,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            volume_ratio=1.5,
        )
        fg = analyzer._calculate_fear_greed(prices, volumes, indicators)
        assert fg > 50

    def test_no_indicators(self, analyzer):
        prices = [100.0]
        volumes = [1000.0]
        indicators = MarketIndicators(
            rsi_14=None,
            ma_5=None,
            ma_20=None,
            ma_60=None,
            macd=None,
            macd_signal=None,
            macd_histogram=None,
            volume_ratio=None,
        )
        fg = analyzer._calculate_fear_greed(prices, volumes, indicators)
        assert fg == 50.0


class TestGenerateRecommendation:
    """Test recommendation generation."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    def test_no_data(self, analyzer):
        rec = analyzer._generate_recommendation(None, None)
        assert "데이터가 부족" in rec

    def test_extreme_fear_recommendation(self, analyzer):
        indicators = MarketIndicators(
            rsi_14=25.0, ma_5=None, ma_20=None, ma_60=None,
            macd=None, macd_signal=None, macd_histogram=None, volume_ratio=None
        )
        kospi = MarketState(
            index_code="KOSPI",
            current_price=2500.0,
            change_pct=-2.5,
            trend=MarketTrend.DOWNTREND,
            fear_greed_index=15.0,
            sentiment=MarketSentiment.EXTREME_FEAR,
            indicators=indicators,
            analysis_date=date.today(),
        )
        rec = analyzer._generate_recommendation(kospi, None)
        assert "극도의 공포" in rec
        assert "역발상" in rec

    def test_extreme_greed_recommendation(self, analyzer):
        indicators = MarketIndicators(
            rsi_14=75.0, ma_5=None, ma_20=None, ma_60=None,
            macd=None, macd_signal=None, macd_histogram=None, volume_ratio=None
        )
        kospi = MarketState(
            index_code="KOSPI",
            current_price=3000.0,
            change_pct=2.5,
            trend=MarketTrend.UPTREND,
            fear_greed_index=85.0,
            sentiment=MarketSentiment.EXTREME_GREED,
            indicators=indicators,
            analysis_date=date.today(),
        )
        rec = analyzer._generate_recommendation(kospi, None)
        assert "과열" in rec
        assert "차익 실현" in rec

    def test_oversold_rsi_recommendation(self, analyzer):
        indicators = MarketIndicators(
            rsi_14=25.0, ma_5=None, ma_20=None, ma_60=None,
            macd=None, macd_signal=None, macd_histogram=None, volume_ratio=None
        )
        kospi = MarketState(
            index_code="KOSPI",
            current_price=2500.0,
            change_pct=-1.0,
            trend=MarketTrend.SIDEWAYS,
            fear_greed_index=40.0,
            sentiment=MarketSentiment.FEAR,
            indicators=indicators,
            analysis_date=date.today(),
        )
        rec = analyzer._generate_recommendation(kospi, None)
        assert "과매도" in rec

    def test_overbought_rsi_recommendation(self, analyzer):
        indicators = MarketIndicators(
            rsi_14=75.0, ma_5=None, ma_20=None, ma_60=None,
            macd=None, macd_signal=None, macd_histogram=None, volume_ratio=None
        )
        kospi = MarketState(
            index_code="KOSPI",
            current_price=3000.0,
            change_pct=1.0,
            trend=MarketTrend.SIDEWAYS,
            fear_greed_index=60.0,
            sentiment=MarketSentiment.NEUTRAL,
            indicators=indicators,
            analysis_date=date.today(),
        )
        rec = analyzer._generate_recommendation(kospi, None)
        assert "과매수" in rec


class TestCalculateIndicators:
    """Test indicator calculation."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    def test_calculate_all_indicators(self, analyzer):
        prices = list(range(100, 200))
        volumes = [1000.0] * 100
        
        indicators = analyzer._calculate_indicators(prices, volumes)
        
        assert indicators.rsi_14 is not None
        assert indicators.ma_5 is not None
        assert indicators.ma_20 is not None
        assert indicators.ma_60 is not None
        assert indicators.macd is not None
        assert indicators.volume_ratio is not None

    def test_calculate_volume_ratio(self, analyzer):
        prices = list(range(100, 125))
        volumes = [1000.0] * 24 + [2000.0]
        
        indicators = analyzer._calculate_indicators(prices, volumes)
        
        assert indicators.volume_ratio == pytest.approx(2.0, rel=0.1)

    def test_insufficient_data_for_ma60(self, analyzer):
        prices = list(range(100, 130))
        volumes = [1000.0] * 30
        
        indicators = analyzer._calculate_indicators(prices, volumes)
        
        assert indicators.ma_5 is not None
        assert indicators.ma_20 is not None
        assert indicators.ma_60 is None


class TestAnalyzeIndex:
    """Test analyze_index method."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    @pytest.fixture
    def mock_price_data(self):
        class MockStockPrice:
            def __init__(self, close, volume, trade_date):
                self.close_price = close
                self.volume = volume
                self.trade_date = trade_date

        return [
            MockStockPrice(100.0 + i * 0.5, 1000000, date(2025, 1, 1))
            for i in range(80)
        ]

    @pytest.mark.asyncio
    async def test_analyze_index_success(self, analyzer, mock_price_data):
        analyzer._get_price_data = AsyncMock(return_value=mock_price_data)
        
        result = await analyzer.analyze_index("KOSPI", date(2025, 3, 1))
        
        assert result.index_code == "KOSPI"
        assert result.current_price == pytest.approx(139.5, rel=0.01)
        assert result.trend in [MarketTrend.UPTREND, MarketTrend.DOWNTREND, MarketTrend.SIDEWAYS]
        assert 0 <= result.fear_greed_index <= 100

    @pytest.mark.asyncio
    async def test_analyze_index_insufficient_data(self, analyzer):
        analyzer._get_price_data = AsyncMock(return_value=[])
        
        with pytest.raises(InsufficientDataError):
            await analyzer.analyze_index("KOSPI", date(2025, 3, 1))


class TestAnalyzeMarket:
    """Test full market analysis."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def analyzer(self, mock_db):
        return MarketAnalyzer(mock_db)

    @pytest.fixture
    def mock_market_state(self):
        indicators = MarketIndicators(
            rsi_14=50.0, ma_5=100.0, ma_20=100.0, ma_60=100.0,
            macd=0.0, macd_signal=0.0, macd_histogram=0.0, volume_ratio=1.0
        )
        return MarketState(
            index_code="KOSPI",
            current_price=2500.0,
            change_pct=0.5,
            trend=MarketTrend.SIDEWAYS,
            fear_greed_index=50.0,
            sentiment=MarketSentiment.NEUTRAL,
            indicators=indicators,
            analysis_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_analyze_market_both_available(self, analyzer, mock_market_state):
        kosdaq_state = MarketState(
            index_code="KOSDAQ",
            current_price=800.0,
            change_pct=0.3,
            trend=MarketTrend.SIDEWAYS,
            fear_greed_index=55.0,
            sentiment=MarketSentiment.NEUTRAL,
            indicators=mock_market_state.indicators,
            analysis_date=date.today(),
        )
        
        with patch.object(analyzer, '_analyze_index') as mock:
            mock.side_effect = [mock_market_state, kosdaq_state]
            
            result = await analyzer.analyze_market()
            
            assert result.kospi is not None
            assert result.kosdaq is not None
            assert "중립" in result.recommendation

    @pytest.mark.asyncio
    async def test_analyze_market_only_kospi(self, analyzer, mock_market_state):
        with patch.object(analyzer, '_analyze_index') as mock:
            mock.side_effect = [mock_market_state, None]
            
            result = await analyzer.analyze_market()
            
            assert result.kospi is not None
            assert result.kosdaq is None

    @pytest.mark.asyncio
    async def test_analyze_market_no_data(self, analyzer):
        with patch.object(analyzer, '_analyze_index') as mock:
            mock.return_value = None
            
            result = await analyzer.analyze_market()
            
            assert result.kospi is None
            assert result.kosdaq is None
            assert "데이터가 부족" in result.recommendation
