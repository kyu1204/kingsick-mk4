"""Unit tests for AIRecommender service."""

import math
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services.ai_recommender import (
    AIRecommender,
    IndicatorScores,
    SignalStrength,
    StockRecommendation,
)


class TestSignalStrength:

    def test_signal_values(self):
        assert SignalStrength.STRONG_BUY.value == "STRONG_BUY"
        assert SignalStrength.BUY.value == "BUY"
        assert SignalStrength.HOLD.value == "HOLD"
        assert SignalStrength.SELL.value == "SELL"
        assert SignalStrength.STRONG_SELL.value == "STRONG_SELL"


class TestIndicatorScores:

    def test_create_scores(self):
        scores = IndicatorScores(
            rsi_score=80.0,
            macd_score=60.0,
            volume_score=70.0,
            trend_score=65.0,
            bollinger_score=75.0,
        )
        assert scores.rsi_score == 80.0
        assert scores.macd_score == 60.0


class TestRSIToScore:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_extreme_oversold(self, recommender):
        score = recommender._rsi_to_score(15)
        assert score == 100.0

    def test_oversold_20(self, recommender):
        score = recommender._rsi_to_score(20)
        assert score == 100.0

    def test_oversold_30(self, recommender):
        score = recommender._rsi_to_score(30)
        assert score == 80.0

    def test_oversold_25(self, recommender):
        score = recommender._rsi_to_score(25)
        assert score == 90.0

    def test_extreme_overbought(self, recommender):
        score = recommender._rsi_to_score(85)
        assert score == 0.0

    def test_overbought_80(self, recommender):
        score = recommender._rsi_to_score(80)
        assert score == 0.0

    def test_overbought_70(self, recommender):
        score = recommender._rsi_to_score(70)
        assert score == 20.0

    def test_neutral(self, recommender):
        score = recommender._rsi_to_score(50)
        assert score == 50.0


class TestVolumeToScore:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_volume_spike_2x(self, recommender):
        volumes = [1000.0] * 20 + [2000.0]
        score = recommender._volume_to_score(volumes)
        assert score >= 70

    def test_volume_spike_3x(self, recommender):
        volumes = [1000.0] * 20 + [3000.0]
        score = recommender._volume_to_score(volumes)
        assert score >= 85

    def test_low_volume(self, recommender):
        volumes = [1000.0] * 20 + [400.0]
        score = recommender._volume_to_score(volumes)
        assert score <= 40

    def test_normal_volume(self, recommender):
        volumes = [1000.0] * 21
        score = recommender._volume_to_score(volumes)
        assert 45 <= score <= 55

    def test_insufficient_data(self, recommender):
        volumes = [1000.0] * 10
        score = recommender._volume_to_score(volumes)
        assert score == 50.0


class TestTrendToScore:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_strong_uptrend(self, recommender):
        ma_5 = [math.nan] * 4 + [105.0] * 10
        ma_20 = [math.nan] * 19 + [100.0] * 5
        ma_60 = [math.nan] * 59 + [95.0] * 5

        score = recommender._trend_to_score(110.0, ma_5, ma_20, ma_60)
        assert score >= 70

    def test_strong_downtrend(self, recommender):
        ma_5 = [math.nan] * 4 + [95.0] * 10
        ma_20 = [math.nan] * 19 + [100.0] * 5
        ma_60 = [math.nan] * 59 + [105.0] * 5

        score = recommender._trend_to_score(90.0, ma_5, ma_20, ma_60)
        assert score <= 30

    def test_sideways(self, recommender):
        ma_5 = [math.nan] * 4 + [100.0] * 10
        ma_20 = [math.nan] * 19 + [100.0] * 5
        ma_60 = []

        score = recommender._trend_to_score(100.0, ma_5, ma_20, ma_60)
        assert 40 <= score <= 60


class TestBollingerToScore:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_below_lower_band(self, recommender):
        upper = [math.nan] * 19 + [110.0]
        lower = [math.nan] * 19 + [90.0]

        score = recommender._bollinger_to_score(85.0, upper, lower)
        assert score >= 90

    def test_above_upper_band(self, recommender):
        upper = [math.nan] * 19 + [110.0]
        lower = [math.nan] * 19 + [90.0]

        score = recommender._bollinger_to_score(115.0, upper, lower)
        assert score <= 10

    def test_at_middle(self, recommender):
        upper = [math.nan] * 19 + [110.0]
        lower = [math.nan] * 19 + [90.0]

        score = recommender._bollinger_to_score(100.0, upper, lower)
        assert 45 <= score <= 55


class TestCalculateTotalScore:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_high_score(self, recommender):
        scores = IndicatorScores(
            rsi_score=90.0,
            macd_score=80.0,
            volume_score=75.0,
            trend_score=85.0,
            bollinger_score=80.0,
        )
        total = recommender._calculate_total_score(scores)
        assert total >= 80

    def test_low_score(self, recommender):
        scores = IndicatorScores(
            rsi_score=20.0,
            macd_score=25.0,
            volume_score=30.0,
            trend_score=20.0,
            bollinger_score=15.0,
        )
        total = recommender._calculate_total_score(scores)
        assert total <= 25

    def test_neutral_score(self, recommender):
        scores = IndicatorScores(
            rsi_score=50.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        total = recommender._calculate_total_score(scores)
        assert total == 50.0


class TestClassifySignal:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_strong_buy(self, recommender):
        scores = IndicatorScores(
            rsi_score=85.0,
            macd_score=80.0,
            volume_score=75.0,
            trend_score=80.0,
            bollinger_score=80.0,
        )
        signal = recommender._classify_signal(80, scores)
        assert signal == SignalStrength.STRONG_BUY

    def test_buy(self, recommender):
        scores = IndicatorScores(
            rsi_score=65.0,
            macd_score=60.0,
            volume_score=55.0,
            trend_score=60.0,
            bollinger_score=55.0,
        )
        signal = recommender._classify_signal(65, scores)
        assert signal == SignalStrength.BUY

    def test_hold(self, recommender):
        scores = IndicatorScores(
            rsi_score=50.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        signal = recommender._classify_signal(50, scores)
        assert signal == SignalStrength.HOLD

    def test_sell(self, recommender):
        scores = IndicatorScores(
            rsi_score=35.0,
            macd_score=30.0,
            volume_score=40.0,
            trend_score=30.0,
            bollinger_score=35.0,
        )
        signal = recommender._classify_signal(35, scores)
        assert signal == SignalStrength.SELL

    def test_strong_sell(self, recommender):
        scores = IndicatorScores(
            rsi_score=15.0,
            macd_score=20.0,
            volume_score=25.0,
            trend_score=15.0,
            bollinger_score=20.0,
        )
        signal = recommender._classify_signal(20, scores)
        assert signal == SignalStrength.STRONG_SELL


class TestGenerateReasons:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    def test_oversold_reason(self, recommender):
        scores = IndicatorScores(
            rsi_score=85.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        reasons = recommender._generate_reasons(scores, SignalStrength.BUY)
        assert any("과매도" in r for r in reasons)

    def test_overbought_reason(self, recommender):
        scores = IndicatorScores(
            rsi_score=15.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        reasons = recommender._generate_reasons(scores, SignalStrength.SELL)
        assert any("과매수" in r for r in reasons)

    def test_volume_spike_reason(self, recommender):
        scores = IndicatorScores(
            rsi_score=50.0,
            macd_score=50.0,
            volume_score=80.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        reasons = recommender._generate_reasons(scores, SignalStrength.HOLD)
        assert any("거래량 급증" in r for r in reasons)

    def test_uptrend_reason(self, recommender):
        scores = IndicatorScores(
            rsi_score=50.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=80.0,
            bollinger_score=50.0,
        )
        reasons = recommender._generate_reasons(scores, SignalStrength.BUY)
        assert any("정배열" in r for r in reasons)

    def test_no_special_signals(self, recommender):
        scores = IndicatorScores(
            rsi_score=50.0,
            macd_score=50.0,
            volume_score=50.0,
            trend_score=50.0,
            bollinger_score=50.0,
        )
        reasons = recommender._generate_reasons(scores, SignalStrength.HOLD)
        assert len(reasons) >= 1


class TestAnalyzeStock:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    @pytest.fixture
    def mock_price_data(self):
        return [
            {
                "date": "20250101",
                "open": 50000.0 + i * 100,
                "high": 51000.0 + i * 100,
                "low": 49000.0 + i * 100,
                "close": 50000.0 + i * 100,
                "volume": 1000000,
            }
            for i in range(80)
        ]

    @pytest.mark.asyncio
    async def test_analyze_stock_success(self, recommender, mock_price_data):
        recommender._get_price_data = AsyncMock(return_value=mock_price_data)

        result = await recommender._analyze_stock("005930", date(2025, 3, 1))

        assert result is not None
        assert result.stock_code == "005930"
        assert 0 <= result.score <= 100
        assert result.signal in SignalStrength
        assert len(result.reasons) >= 1

    @pytest.mark.asyncio
    async def test_analyze_stock_insufficient_data(self, recommender):
        recommender._get_price_data = AsyncMock(return_value=[])

        result = await recommender._analyze_stock("005930", date(2025, 3, 1))

        assert result is None


class TestGetRecommendations:

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def recommender(self, mock_db):
        return AIRecommender(mock_db)

    @pytest.mark.asyncio
    async def test_get_recommendations_empty(self, recommender):
        recommender._get_stock_codes = AsyncMock(return_value=[])

        result = await recommender.get_recommendations()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_recommendations_sorted(self, recommender):
        rec1 = StockRecommendation(
            stock_code="A", stock_name="A", current_price=100, change_pct=1.0,
            score=70, signal=SignalStrength.BUY,
            indicator_scores=IndicatorScores(70, 70, 70, 70, 70),
            reasons=["test"], analysis_date=date.today()
        )
        rec2 = StockRecommendation(
            stock_code="B", stock_name="B", current_price=100, change_pct=1.0,
            score=80, signal=SignalStrength.BUY,
            indicator_scores=IndicatorScores(80, 80, 80, 80, 80),
            reasons=["test"], analysis_date=date.today()
        )

        recommender._get_stock_codes = AsyncMock(return_value=["A", "B"])
        recommender._analyze_stock = AsyncMock(side_effect=[rec1, rec2])

        result = await recommender.get_recommendations(top_n=2)

        assert len(result) == 2
        assert result[0].score == 80
        assert result[1].score == 70
