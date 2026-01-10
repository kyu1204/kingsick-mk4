"""Integration tests for Market Analysis API endpoints."""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User
from app.services.auth import create_access_token
from app.services.market_analyzer import (
    MarketIndicators,
    MarketSentiment,
    MarketState,
    MarketTrend,
)


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
    return db


@pytest.fixture
def mock_market_state():
    indicators = MarketIndicators(
        rsi_14=50.0,
        ma_5=2500.0,
        ma_20=2480.0,
        ma_60=2450.0,
        macd=5.0,
        macd_signal=4.0,
        macd_histogram=1.0,
        volume_ratio=1.2,
    )
    return MarketState(
        index_code="KOSPI",
        current_price=2520.0,
        change_pct=0.5,
        trend=MarketTrend.SIDEWAYS,
        fear_greed_index=55.0,
        sentiment=MarketSentiment.NEUTRAL,
        indicators=indicators,
        analysis_date=date.today(),
    )


class TestMarketAnalysisAPI:

    @pytest.mark.asyncio
    async def test_get_market_analysis_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/market")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_market_analysis_success(self, mock_user, mock_db, auth_headers, mock_market_state):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_market = AsyncMock(return_value=type("Result", (), {
                "kospi": mock_market_state,
                "kosdaq": None,
                "recommendation": "시장이 중립적인 상태입니다.",
                "analysis_date": date.today(),
            })())

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["kospi"] is not None
                    assert data["kospi"]["index_code"] == "KOSPI"
                    assert data["kospi"]["current_price"] == 2520.0
                    assert data["kospi"]["trend"] == "SIDEWAYS"
                    assert data["kospi"]["fear_greed_index"] == 55.0
                    assert data["kosdaq"] is None
                    assert "중립" in data["recommendation"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_market_analysis_with_date(self, mock_user, mock_db, auth_headers, mock_market_state):
        target_date = date.today() - timedelta(days=7)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_market = AsyncMock(return_value=type("Result", (), {
                "kospi": mock_market_state,
                "kosdaq": None,
                "recommendation": "테스트",
                "analysis_date": target_date,
            })())

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        f"/api/v1/analysis/market?target_date={target_date.isoformat()}",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["analysis_date"] == target_date.isoformat()
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_market_analysis_no_data(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_market = AsyncMock(return_value=type("Result", (), {
                "kospi": None,
                "kosdaq": None,
                "recommendation": "분석 데이터가 부족합니다.",
                "analysis_date": date.today(),
            })())

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["kospi"] is None
                    assert data["kosdaq"] is None
            finally:
                app.dependency_overrides.clear()


class TestIndexAnalysisAPI:

    @pytest.mark.asyncio
    async def test_get_index_analysis_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/market/KOSPI")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_index_analysis_invalid_code(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/analysis/market/INVALID", headers=auth_headers)
                assert response.status_code == 400
                assert "Invalid index code" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kospi_analysis_success(self, mock_user, mock_db, auth_headers, mock_market_state):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_index = AsyncMock(return_value=mock_market_state)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market/KOSPI", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["index_code"] == "KOSPI"
                    assert data["current_price"] == 2520.0
                    assert data["indicators"]["rsi_14"] == 50.0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_kosdaq_analysis_success(self, mock_user, mock_db, auth_headers):
        kosdaq_state = MarketState(
            index_code="KOSDAQ",
            current_price=850.0,
            change_pct=-0.3,
            trend=MarketTrend.DOWNTREND,
            fear_greed_index=35.0,
            sentiment=MarketSentiment.FEAR,
            indicators=MarketIndicators(
                rsi_14=35.0, ma_5=860.0, ma_20=880.0, ma_60=900.0,
                macd=-2.0, macd_signal=-1.5, macd_histogram=-0.5, volume_ratio=0.8
            ),
            analysis_date=date.today(),
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_index = AsyncMock(return_value=kosdaq_state)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market/KOSDAQ", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["index_code"] == "KOSDAQ"
                    assert data["trend"] == "DOWNTREND"
                    assert data["sentiment"] == "FEAR"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_index_analysis_insufficient_data(self, mock_user, mock_db, auth_headers):
        from app.services.market_analyzer import InsufficientDataError

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_index = AsyncMock(side_effect=InsufficientDataError("No data"))

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market/KOSPI", headers=auth_headers)
                    assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_index_case_insensitive(self, mock_user, mock_db, auth_headers, mock_market_state):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze_index = AsyncMock(return_value=mock_market_state)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/market/kospi", headers=auth_headers)
                    assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()


class TestStockStateAPI:

    @pytest.mark.asyncio
    async def test_get_stock_state_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/stock/005930/state")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stock_state_success(self, mock_user, mock_db, auth_headers):
        stock_state = MarketState(
            index_code="005930",
            current_price=72000.0,
            change_pct=1.2,
            trend=MarketTrend.UPTREND,
            fear_greed_index=65.0,
            sentiment=MarketSentiment.GREED,
            indicators=MarketIndicators(
                rsi_14=62.0, ma_5=71500.0, ma_20=70000.0, ma_60=68000.0,
                macd=500.0, macd_signal=400.0, macd_histogram=100.0, volume_ratio=1.3
            ),
            analysis_date=date.today(),
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.get_stock_market_state = AsyncMock(return_value=stock_state)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/stock/005930/state", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["stock_code"] == "005930"
                    assert data["current_price"] == 72000.0
                    assert data["trend"] == "UPTREND"
                    assert data["indicators"]["rsi_14"] == 62.0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stock_state_insufficient_data(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.get_stock_market_state = AsyncMock(return_value=None)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/stock/999999/state", headers=auth_headers)

                    assert response.status_code == 404
                    assert "Insufficient data" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stock_state_with_date(self, mock_user, mock_db, auth_headers):
        target_date = date.today() - timedelta(days=30)
        stock_state = MarketState(
            index_code="005930",
            current_price=70000.0,
            change_pct=0.5,
            trend=MarketTrend.SIDEWAYS,
            fear_greed_index=50.0,
            sentiment=MarketSentiment.NEUTRAL,
            indicators=MarketIndicators(
                rsi_14=50.0, ma_5=70000.0, ma_20=70000.0, ma_60=70000.0,
                macd=0.0, macd_signal=0.0, macd_histogram=0.0, volume_ratio=1.0
            ),
            analysis_date=target_date,
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.MarketAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.get_stock_market_state = AsyncMock(return_value=stock_state)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        f"/api/v1/analysis/stock/005930/state?target_date={target_date.isoformat()}",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["analysis_date"] == target_date.isoformat()
            finally:
                app.dependency_overrides.clear()


class TestRecommendationsAPI:
    """Tests for AI recommendation endpoints."""

    @pytest.fixture
    def mock_recommendation(self):
        from app.services.ai_recommender import IndicatorScores, SignalStrength, StockRecommendation
        return StockRecommendation(
            stock_code="005930",
            stock_name="삼성전자",
            current_price=72000.0,
            change_pct=1.2,
            score=75.5,
            signal=SignalStrength.BUY,
            indicator_scores=IndicatorScores(
                rsi_score=80.0,
                macd_score=65.0,
                volume_score=70.0,
                trend_score=75.0,
                bollinger_score=80.0,
            ),
            reasons=["RSI 과매도 구간 (매수 기회)", "볼린저 밴드 하단 이탈 (반등 기대)"],
            analysis_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_get_recommendations_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/recommend")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, mock_user, mock_db, auth_headers, mock_recommendation):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.get_recommendations = AsyncMock(return_value=[mock_recommendation])

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/recommend", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == 1
                    assert len(data["recommendations"]) == 1
                    rec = data["recommendations"][0]
                    assert rec["stock_code"] == "005930"
                    assert rec["score"] == 75.5
                    assert rec["signal"] == "BUY"
                    assert "indicator_scores" in rec
                    assert rec["indicator_scores"]["rsi_score"] == 80.0
                    assert len(rec["reasons"]) == 2
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recommendations_empty(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.get_recommendations = AsyncMock(return_value=[])

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/recommend", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == 0
                    assert data["recommendations"] == []
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_recommendations_with_top_n(self, mock_user, mock_db, auth_headers, mock_recommendation):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.get_recommendations = AsyncMock(return_value=[mock_recommendation])

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        "/api/v1/analysis/recommend?top_n=5",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    mock_instance.get_recommendations.assert_called_once()
                    call_kwargs = mock_instance.get_recommendations.call_args.kwargs
                    assert call_kwargs.get("top_n") == 5
            finally:
                app.dependency_overrides.clear()


class TestBuySellSignalsAPI:
    """Tests for buy/sell signal filter endpoints."""

    @pytest.fixture
    def mock_buy_recommendation(self):
        from app.services.ai_recommender import IndicatorScores, SignalStrength, StockRecommendation
        return StockRecommendation(
            stock_code="005930",
            stock_name="삼성전자",
            current_price=72000.0,
            change_pct=1.2,
            score=80.0,
            signal=SignalStrength.STRONG_BUY,
            indicator_scores=IndicatorScores(
                rsi_score=90.0, macd_score=75.0, volume_score=80.0,
                trend_score=85.0, bollinger_score=85.0,
            ),
            reasons=["RSI 과매도 구간 (매수 기회)"],
            analysis_date=date.today(),
        )

    @pytest.fixture
    def mock_sell_recommendation(self):
        from app.services.ai_recommender import IndicatorScores, SignalStrength, StockRecommendation
        return StockRecommendation(
            stock_code="066570",
            stock_name="LG전자",
            current_price=95000.0,
            change_pct=-2.1,
            score=25.0,
            signal=SignalStrength.SELL,
            indicator_scores=IndicatorScores(
                rsi_score=15.0, macd_score=25.0, volume_score=30.0,
                trend_score=20.0, bollinger_score=25.0,
            ),
            reasons=["RSI 과매수 구간 (매도 고려)"],
            analysis_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_get_buy_signals_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/recommend/buy")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_buy_signals_success(self, mock_user, mock_db, auth_headers, mock_buy_recommendation):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.get_buy_signals = AsyncMock(return_value=[mock_buy_recommendation])

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/recommend/buy", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == 1
                    rec = data["recommendations"][0]
                    assert rec["signal"] == "STRONG_BUY"
                    assert rec["score"] == 80.0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_sell_signals_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/recommend/sell")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_sell_signals_success(self, mock_user, mock_db, auth_headers, mock_sell_recommendation):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.get_sell_signals = AsyncMock(return_value=[mock_sell_recommendation])

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/recommend/sell", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] == 1
                    rec = data["recommendations"][0]
                    assert rec["signal"] == "SELL"
                    assert rec["score"] == 25.0
            finally:
                app.dependency_overrides.clear()


class TestStockScoreAPI:
    """Tests for individual stock score endpoint."""

    @pytest.fixture
    def mock_stock_score(self):
        from app.services.ai_recommender import IndicatorScores, SignalStrength, StockRecommendation
        return StockRecommendation(
            stock_code="005930",
            stock_name="005930",
            current_price=72000.0,
            change_pct=1.5,
            score=65.0,
            signal=SignalStrength.BUY,
            indicator_scores=IndicatorScores(
                rsi_score=70.0, macd_score=60.0, volume_score=55.0,
                trend_score=70.0, bollinger_score=65.0,
            ),
            reasons=["복합 지표 매수 신호"],
            analysis_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_get_stock_score_no_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analysis/stock/005930/score")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stock_score_success(self, mock_user, mock_db, auth_headers, mock_stock_score):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.score_stock = AsyncMock(return_value=mock_stock_score)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/stock/005930/score", headers=auth_headers)

                    assert response.status_code == 200
                    data = response.json()
                    assert data["stock_code"] == "005930"
                    assert data["score"] == 65.0
                    assert data["signal"] == "BUY"
                    assert "indicator_scores" in data
                    assert data["indicator_scores"]["rsi_score"] == 70.0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stock_score_not_found(self, mock_user, mock_db, auth_headers):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.score_stock = AsyncMock(return_value=None)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/analysis/stock/999999/score", headers=auth_headers)

                    assert response.status_code == 404
                    assert "Insufficient data" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stock_score_with_date(self, mock_user, mock_db, auth_headers, mock_stock_score):
        target_date = date.today() - timedelta(days=7)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.analysis.AIRecommender") as MockRecommender:
            mock_instance = MockRecommender.return_value
            mock_instance.score_stock = AsyncMock(return_value=mock_stock_score)

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        f"/api/v1/analysis/stock/005930/score?target_date={target_date.isoformat()}",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    mock_instance.score_stock.assert_called_once_with("005930", target_date)
            finally:
                app.dependency_overrides.clear()
