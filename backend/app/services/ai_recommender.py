"""AI Stock Recommender Service.

Provides stock recommendations based on BNF strategy scoring.
Analyzes stocks using technical indicators and generates buy/sell signals.
"""

import math
from dataclasses import dataclass
from datetime import date
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bnf_strategy import BNFStrategy
from app.models.backtest import StockPrice
from app.models.watchlist import WatchlistItem
from app.services.indicator import IndicatorCalculator


class SignalStrength(str, Enum):
    """Signal strength classification."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class IndicatorScores:
    """Individual indicator scores for transparency."""

    rsi_score: float
    macd_score: float
    volume_score: float
    trend_score: float
    bollinger_score: float


@dataclass
class StockRecommendation:
    """Stock recommendation result."""

    stock_code: str
    stock_name: str
    current_price: float
    change_pct: float
    score: float
    signal: SignalStrength
    indicator_scores: IndicatorScores
    reasons: list[str]
    analysis_date: date


class AIRecommenderError(Exception):
    """Base exception for AI recommender."""

    pass


class NoStocksError(AIRecommenderError):
    """No stocks available for analysis."""

    pass


class AIRecommender:
    """AI-powered stock recommender.

    Uses BNF strategy and technical indicators to score stocks
    and generate buy/sell recommendations.
    """

    MIN_DATA_POINTS = 60
    LOOKBACK_PERIOD = 100

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.indicator = IndicatorCalculator()
        self.strategy = BNFStrategy()

    async def get_recommendations(
        self,
        user_id: str | None = None,
        top_n: int = 10,
        target_date: date | None = None,
    ) -> list[StockRecommendation]:
        """Get top stock recommendations.

        Args:
            user_id: User ID for filtering watchlist stocks (optional)
            top_n: Number of top recommendations to return
            target_date: Date for analysis (default: today)

        Returns:
            List of StockRecommendation sorted by score descending
        """
        if target_date is None:
            target_date = date.today()

        stock_codes = await self._get_stock_codes(user_id)

        if not stock_codes:
            return []

        recommendations: list[StockRecommendation] = []

        for stock_code in stock_codes:
            rec = await self._analyze_stock(stock_code, target_date)
            if rec:
                recommendations.append(rec)

        recommendations.sort(key=lambda r: r.score, reverse=True)

        return recommendations[:top_n]

    async def score_stock(
        self,
        stock_code: str,
        target_date: date | None = None,
    ) -> StockRecommendation | None:
        """Score a single stock.

        Args:
            stock_code: Stock code to analyze
            target_date: Date for analysis

        Returns:
            StockRecommendation or None if insufficient data
        """
        if target_date is None:
            target_date = date.today()

        return await self._analyze_stock(stock_code, target_date)

    async def get_buy_signals(
        self,
        user_id: str | None = None,
        top_n: int = 10,
        target_date: date | None = None,
    ) -> list[StockRecommendation]:
        """Get stocks with buy signals only.

        Args:
            user_id: User ID for filtering
            top_n: Number of recommendations
            target_date: Date for analysis

        Returns:
            List of buy recommendations
        """
        all_recs = await self.get_recommendations(user_id, top_n * 3, target_date)
        buy_signals = [r for r in all_recs if r.signal in [SignalStrength.BUY, SignalStrength.STRONG_BUY]]
        return buy_signals[:top_n]

    async def get_sell_signals(
        self,
        user_id: str | None = None,
        top_n: int = 10,
        target_date: date | None = None,
    ) -> list[StockRecommendation]:
        """Get stocks with sell signals only.

        Args:
            user_id: User ID for filtering
            top_n: Number of recommendations
            target_date: Date for analysis

        Returns:
            List of sell recommendations (lowest scores)
        """
        all_recs = await self.get_recommendations(user_id, top_n * 3, target_date)
        sell_signals = [r for r in all_recs if r.signal in [SignalStrength.SELL, SignalStrength.STRONG_SELL]]
        sell_signals.sort(key=lambda r: r.score)
        return sell_signals[:top_n]

    async def _get_stock_codes(self, user_id: str | None) -> list[str]:
        """Get stock codes to analyze.

        If user_id provided, gets from user's watchlist.
        Otherwise returns stocks with price data.
        """
        if user_id:
            query = select(WatchlistItem.stock_code).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.is_active == True,  # noqa: E712
            )
            result = await self.db.execute(query)
            codes = list(result.scalars().all())
            if codes:
                return codes

        query = select(StockPrice.stock_code).distinct().limit(100)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_price_data(
        self,
        stock_code: str,
        target_date: date,
    ) -> list[StockPrice]:
        """Get historical price data for stock."""
        query = (
            select(StockPrice)
            .where(StockPrice.stock_code == stock_code)
            .where(StockPrice.trade_date <= target_date)
            .order_by(StockPrice.trade_date.asc())
            .limit(self.LOOKBACK_PERIOD)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _analyze_stock(
        self,
        stock_code: str,
        target_date: date,
    ) -> StockRecommendation | None:
        """Analyze a single stock and generate recommendation."""
        prices = await self._get_price_data(stock_code, target_date)

        if len(prices) < self.MIN_DATA_POINTS:
            return None

        close_prices = [p.close_price for p in prices]
        volumes = [float(p.volume) for p in prices]
        high_prices = [p.high_price for p in prices]
        low_prices = [p.low_price for p in prices]

        scores = self._calculate_indicator_scores(close_prices, volumes, high_prices, low_prices)
        total_score = self._calculate_total_score(scores)
        signal = self._classify_signal(total_score, scores)
        reasons = self._generate_reasons(scores, signal)

        current_price = close_prices[-1]
        prev_price = close_prices[-2] if len(close_prices) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0

        return StockRecommendation(
            stock_code=stock_code,
            stock_name=stock_code,
            current_price=current_price,
            change_pct=round(change_pct, 2),
            score=round(total_score, 1),
            signal=signal,
            indicator_scores=scores,
            reasons=reasons,
            analysis_date=target_date,
        )

    def _calculate_indicator_scores(
        self,
        prices: list[float],
        volumes: list[float],
        highs: list[float],
        lows: list[float],
    ) -> IndicatorScores:
        """Calculate individual indicator scores (0-100 scale)."""
        rsi_values = self.indicator.calculate_rsi(prices, 14)
        rsi = rsi_values[-1] if rsi_values and not math.isnan(rsi_values[-1]) else 50.0

        rsi_score = self._rsi_to_score(rsi)

        macd_line, signal_line, histogram = self.indicator.calculate_macd(prices)
        macd_score = self._macd_to_score(macd_line, signal_line, histogram, prices[-1] if prices else 1.0)

        volume_score = self._volume_to_score(volumes)

        ma_5 = self.indicator.calculate_sma(prices, 5)
        ma_20 = self.indicator.calculate_sma(prices, 20)
        ma_60 = self.indicator.calculate_sma(prices, 60)
        trend_score = self._trend_to_score(prices[-1], ma_5, ma_20, ma_60)

        upper, middle, lower = self.indicator.calculate_bollinger_bands(prices, 20, 2.0)
        bollinger_score = self._bollinger_to_score(prices[-1], upper, lower)

        return IndicatorScores(
            rsi_score=round(rsi_score, 1),
            macd_score=round(macd_score, 1),
            volume_score=round(volume_score, 1),
            trend_score=round(trend_score, 1),
            bollinger_score=round(bollinger_score, 1),
        )

    def _rsi_to_score(self, rsi: float) -> float:
        """Convert RSI to contrarian score (low RSI = high score for BNF)."""
        if rsi <= 20:
            return 100.0
        elif rsi <= 30:
            return 80 + (30 - rsi) * 2
        elif rsi >= 80:
            return 0.0
        elif rsi >= 70:
            return 20 - (rsi - 70) * 2
        else:
            return 50.0

    def _macd_to_score(
        self,
        macd_line: list[float],
        signal_line: list[float],
        histogram: list[float],
        current_price: float,
    ) -> float:
        """Convert MACD to score based on crossover signals."""
        if not histogram or len(histogram) < 2:
            return 50.0

        hist_current = histogram[-1]
        hist_prev = histogram[-2]

        if math.isnan(hist_current) or math.isnan(hist_prev):
            return 50.0

        normalized = (hist_current / current_price) * 10000

        if hist_current > 0 and hist_prev <= 0:
            return min(100, 80 + abs(normalized))
        elif hist_current < 0 and hist_prev >= 0:
            return max(0, 20 - abs(normalized))
        elif hist_current > 0:
            return min(100, 50 + normalized * 5)
        else:
            return max(0, 50 + normalized * 5)

    def _volume_to_score(self, volumes: list[float]) -> float:
        """Convert volume trend to score."""
        if len(volumes) < 21:
            return 50.0

        avg_volume = sum(volumes[-21:-1]) / 20
        current_volume = volumes[-1]

        if avg_volume <= 0:
            return 50.0

        ratio = current_volume / avg_volume

        if ratio >= 2.0:
            return min(100, 70 + (ratio - 2.0) * 15)
        elif ratio >= 1.5:
            return 60 + (ratio - 1.5) * 20
        elif ratio <= 0.5:
            return max(0, 40 - (0.5 - ratio) * 40)
        else:
            return 50.0

    def _trend_to_score(
        self,
        current_price: float,
        ma_5: list[float],
        ma_20: list[float],
        ma_60: list[float],
    ) -> float:
        """Convert MA alignment to trend score."""
        if not ma_5 or not ma_20 or not ma_60:
            return 50.0

        ma5 = ma_5[-1] if not math.isnan(ma_5[-1]) else None
        ma20 = ma_20[-1] if not math.isnan(ma_20[-1]) else None
        ma60 = ma_60[-1] if len(ma_60) > 59 and not math.isnan(ma_60[-1]) else None

        if ma5 is None or ma20 is None:
            return 50.0

        score = 50.0

        if current_price > ma5 > ma20:
            score += 20
            if ma60 and ma20 > ma60:
                score += 10
        elif current_price < ma5 < ma20:
            score -= 20
            if ma60 and ma20 < ma60:
                score -= 10

        if ma5 > ma20:
            score += 10
        elif ma5 < ma20:
            score -= 10

        return max(0, min(100, score))

    def _bollinger_to_score(
        self,
        current_price: float,
        upper: list[float],
        lower: list[float],
    ) -> float:
        """Convert Bollinger Band position to contrarian score."""
        if not upper or not lower:
            return 50.0

        upper_val = upper[-1] if not math.isnan(upper[-1]) else None
        lower_val = lower[-1] if not math.isnan(lower[-1]) else None

        if upper_val is None or lower_val is None:
            return 50.0

        band_width = upper_val - lower_val
        if band_width <= 0:
            return 50.0

        position = (current_price - lower_val) / band_width

        if position <= 0:
            return 90 + min(10, abs(position) * 10)
        elif position >= 1:
            return 10 - min(10, (position - 1) * 10)
        else:
            return 50 + (0.5 - position) * 60

    def _calculate_total_score(self, scores: IndicatorScores) -> float:
        """Calculate weighted total score."""
        weights = {
            "rsi": 0.30,
            "macd": 0.20,
            "volume": 0.15,
            "trend": 0.20,
            "bollinger": 0.15,
        }

        total = (
            scores.rsi_score * weights["rsi"]
            + scores.macd_score * weights["macd"]
            + scores.volume_score * weights["volume"]
            + scores.trend_score * weights["trend"]
            + scores.bollinger_score * weights["bollinger"]
        )

        return total

    def _classify_signal(self, score: float, scores: IndicatorScores) -> SignalStrength:
        """Classify signal based on total score and individual indicators."""
        if score >= 75:
            if scores.rsi_score >= 80 and scores.bollinger_score >= 70:
                return SignalStrength.STRONG_BUY
            return SignalStrength.BUY
        elif score >= 60:
            return SignalStrength.BUY
        elif score <= 25:
            if scores.rsi_score <= 20 and scores.bollinger_score <= 30:
                return SignalStrength.STRONG_SELL
            return SignalStrength.SELL
        elif score <= 40:
            return SignalStrength.SELL
        else:
            return SignalStrength.HOLD

    def _generate_reasons(
        self,
        scores: IndicatorScores,
        signal: SignalStrength,
    ) -> list[str]:
        """Generate human-readable reasons for the recommendation."""
        reasons: list[str] = []

        if scores.rsi_score >= 80:
            reasons.append("RSI 과매도 구간 (매수 기회)")
        elif scores.rsi_score <= 20:
            reasons.append("RSI 과매수 구간 (매도 고려)")

        if scores.macd_score >= 70:
            reasons.append("MACD 상향 돌파 신호")
        elif scores.macd_score <= 30:
            reasons.append("MACD 하향 돌파 신호")

        if scores.volume_score >= 70:
            reasons.append("거래량 급증 (관심 증가)")
        elif scores.volume_score <= 30:
            reasons.append("거래량 감소 (관심 저조)")

        if scores.trend_score >= 70:
            reasons.append("이동평균선 정배열 (상승 추세)")
        elif scores.trend_score <= 30:
            reasons.append("이동평균선 역배열 (하락 추세)")

        if scores.bollinger_score >= 80:
            reasons.append("볼린저 밴드 하단 이탈 (반등 기대)")
        elif scores.bollinger_score <= 20:
            reasons.append("볼린저 밴드 상단 이탈 (조정 가능)")

        if not reasons:
            if signal == SignalStrength.HOLD:
                reasons.append("특별한 신호 없음 (관망 권장)")
            elif signal in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
                reasons.append("복합 지표 매수 신호")
            else:
                reasons.append("복합 지표 매도 신호")

        return reasons
