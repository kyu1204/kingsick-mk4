"""Market State Analyzer Service.

Provides analysis of market conditions including:
- KOSPI/KOSDAQ index state analysis
- Trend detection (uptrend/downtrend/sideways)
- Fear-Greed index calculation
- Technical indicator-based market assessment
"""

import math
from dataclasses import dataclass
from datetime import date
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import StockPrice
from app.services.indicator import IndicatorCalculator


class MarketTrend(str, Enum):
    """Market trend classification."""

    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"


class MarketSentiment(str, Enum):
    """Market sentiment classification."""

    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"


@dataclass
class MarketIndicators:
    """Technical indicators for market analysis."""

    rsi_14: float | None
    ma_5: float | None
    ma_20: float | None
    ma_60: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    volume_ratio: float | None


@dataclass
class MarketState:
    """Market state analysis result."""

    index_code: str  # "KOSPI" or "KOSDAQ"
    current_price: float
    change_pct: float
    trend: MarketTrend
    fear_greed_index: float  # 0-100
    sentiment: MarketSentiment
    indicators: MarketIndicators
    analysis_date: date


@dataclass
class MarketAnalysisResult:
    """Combined market analysis result."""

    kospi: MarketState | None
    kosdaq: MarketState | None
    recommendation: str
    analysis_date: date


class MarketAnalyzerError(Exception):
    """Base exception for market analyzer."""

    pass


class InsufficientDataError(MarketAnalyzerError):
    """Not enough data for analysis."""

    pass


class MarketAnalyzer:
    """Market state analyzer.

    Analyzes market conditions using technical indicators
    to determine trend, sentiment, and trading recommendations.
    """

    # Index codes for KOSPI and KOSDAQ
    KOSPI_CODE = "KOSPI"  # 코스피 지수 대용 (실제 KIS API에서는 0001)
    KOSDAQ_CODE = "KOSDAQ"  # 코스닥 지수 대용 (실제 KIS API에서는 1001)

    # Analysis parameters
    MIN_DATA_POINTS = 60  # Minimum days of data required

    def __init__(self, db: AsyncSession) -> None:
        """Initialize market analyzer.

        Args:
            db: Async database session
        """
        self.db = db
        self.indicator = IndicatorCalculator()

    async def analyze_market(
        self,
        target_date: date | None = None,
    ) -> MarketAnalysisResult:
        """Perform full market analysis.

        Args:
            target_date: Date to analyze (default: latest available)

        Returns:
            MarketAnalysisResult with KOSPI, KOSDAQ states and recommendation
        """
        if target_date is None:
            target_date = date.today()

        kospi_state = await self._analyze_index(self.KOSPI_CODE, target_date)
        kosdaq_state = await self._analyze_index(self.KOSDAQ_CODE, target_date)

        recommendation = self._generate_recommendation(kospi_state, kosdaq_state)

        return MarketAnalysisResult(
            kospi=kospi_state,
            kosdaq=kosdaq_state,
            recommendation=recommendation,
            analysis_date=target_date,
        )

    async def analyze_index(
        self,
        index_code: str,
        target_date: date | None = None,
    ) -> MarketState:
        """Analyze single index state.

        Args:
            index_code: Index code (KOSPI or KOSDAQ)
            target_date: Date to analyze

        Returns:
            MarketState for the index

        Raises:
            InsufficientDataError: Not enough data for analysis
        """
        if target_date is None:
            target_date = date.today()

        state = await self._analyze_index(index_code, target_date)
        if state is None:
            raise InsufficientDataError(f"Insufficient data for {index_code} analysis")

        return state

    async def _analyze_index(
        self,
        index_code: str,
        target_date: date,
    ) -> MarketState | None:
        """Internal method to analyze single index.

        Args:
            index_code: Index code
            target_date: Target date for analysis

        Returns:
            MarketState or None if insufficient data
        """
        # Get price data from database
        prices = await self._get_price_data(index_code, target_date)

        if len(prices) < self.MIN_DATA_POINTS:
            return None

        close_prices = [p.close_price for p in prices]
        volumes = [float(p.volume) for p in prices]

        # Calculate indicators
        indicators = self._calculate_indicators(close_prices, volumes)

        # Determine trend
        trend = self._determine_trend(close_prices, indicators)

        # Calculate fear-greed index
        fear_greed = self._calculate_fear_greed(close_prices, volumes, indicators)
        sentiment = self._classify_sentiment(fear_greed)

        # Calculate change percentage
        current_price = close_prices[-1]
        prev_price = close_prices[-2] if len(close_prices) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0

        return MarketState(
            index_code=index_code,
            current_price=current_price,
            change_pct=round(change_pct, 2),
            trend=trend,
            fear_greed_index=round(fear_greed, 1),
            sentiment=sentiment,
            indicators=indicators,
            analysis_date=target_date,
        )

    async def _get_price_data(
        self,
        stock_code: str,
        target_date: date,
    ) -> list[StockPrice]:
        """Get price data from database.

        Args:
            stock_code: Stock/index code
            target_date: End date for data

        Returns:
            List of StockPrice records ordered by date ascending
        """
        query = (
            select(StockPrice)
            .where(StockPrice.stock_code == stock_code)
            .where(StockPrice.trade_date <= target_date)
            .order_by(StockPrice.trade_date.asc())
            .limit(250)  # Max 1 year of trading days
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _calculate_indicators(
        self,
        prices: list[float],
        volumes: list[float],
    ) -> MarketIndicators:
        """Calculate all technical indicators.

        Args:
            prices: Close prices
            volumes: Volume data

        Returns:
            MarketIndicators with calculated values
        """
        # RSI
        rsi_values = self.indicator.calculate_rsi(prices, 14)
        rsi_14 = rsi_values[-1] if rsi_values and not math.isnan(rsi_values[-1]) else None

        # Moving Averages
        ma_5 = self._get_last_valid(self.indicator.calculate_sma(prices, 5))
        ma_20 = self._get_last_valid(self.indicator.calculate_sma(prices, 20))
        ma_60 = self._get_last_valid(self.indicator.calculate_sma(prices, 60))

        # MACD
        macd_line, signal_line, histogram = self.indicator.calculate_macd(prices)
        macd = self._get_last_valid(macd_line)
        macd_signal = self._get_last_valid(signal_line)
        macd_histogram = self._get_last_valid(histogram)

        # Volume ratio (current vs 20-day average)
        volume_ratio = None
        if len(volumes) >= 20:
            avg_volume = (
                sum(volumes[-21:-1]) / 20
                if len(volumes) > 20
                else sum(volumes[:-1]) / (len(volumes) - 1)
            )
            if avg_volume > 0:
                volume_ratio = round(volumes[-1] / avg_volume, 2)

        return MarketIndicators(
            rsi_14=round(rsi_14, 2) if rsi_14 is not None else None,
            ma_5=round(ma_5, 2) if ma_5 is not None else None,
            ma_20=round(ma_20, 2) if ma_20 is not None else None,
            ma_60=round(ma_60, 2) if ma_60 is not None else None,
            macd=round(macd, 4) if macd is not None else None,
            macd_signal=round(macd_signal, 4) if macd_signal is not None else None,
            macd_histogram=round(macd_histogram, 4) if macd_histogram is not None else None,
            volume_ratio=volume_ratio,
        )

    def _get_last_valid(self, values: list[float]) -> float | None:
        """Get last non-NaN value from list.

        Args:
            values: List of float values (may contain NaN)

        Returns:
            Last valid value or None
        """
        if not values:
            return None
        last = values[-1]
        return None if math.isnan(last) else last

    def _determine_trend(
        self,
        prices: list[float],
        indicators: MarketIndicators,
    ) -> MarketTrend:
        """Determine market trend based on indicators.

        Trend is determined by:
        1. Price vs MA alignment (5 > 20 > 60 = uptrend)
        2. MACD histogram direction
        3. Recent price momentum

        Args:
            prices: Close prices
            indicators: Calculated indicators

        Returns:
            MarketTrend classification
        """
        score = 0

        # Check MA alignment
        if indicators.ma_5 and indicators.ma_20 and indicators.ma_60:
            current_price = prices[-1]

            # Price above all MAs = bullish
            if current_price > indicators.ma_5 > indicators.ma_20 > indicators.ma_60:
                score += 3
            # Price below all MAs = bearish
            elif current_price < indicators.ma_5 < indicators.ma_20 < indicators.ma_60:
                score -= 3
            # Price above 20 MA = moderately bullish
            elif current_price > indicators.ma_20:
                score += 1
            else:
                score -= 1

        # MACD histogram
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                score += 1
            elif indicators.macd_histogram < 0:
                score -= 1

        # RSI trend
        if indicators.rsi_14 is not None:
            if indicators.rsi_14 > 60:
                score += 1
            elif indicators.rsi_14 < 40:
                score -= 1

        # Classify trend
        if score >= 3:
            return MarketTrend.UPTREND
        elif score <= -3:
            return MarketTrend.DOWNTREND
        else:
            return MarketTrend.SIDEWAYS

    def _calculate_fear_greed(
        self,
        prices: list[float],
        volumes: list[float],
        indicators: MarketIndicators,
    ) -> float:
        """Calculate Fear-Greed index (0-100).

        Components:
        1. RSI (inverted for fear-greed scale): 25% weight
        2. Price vs MA distance: 25% weight
        3. MACD momentum: 25% weight
        4. Volume ratio: 25% weight

        0 = Extreme Fear, 100 = Extreme Greed

        Args:
            prices: Close prices
            volumes: Volume data
            indicators: Calculated indicators

        Returns:
            Fear-Greed index (0-100)
        """
        components: list[float] = []

        # 1. RSI component (0-100, already in range)
        if indicators.rsi_14 is not None:
            components.append(indicators.rsi_14)

        # 2. Price vs MA20 distance (normalized to 0-100)
        if indicators.ma_20 is not None and indicators.ma_20 > 0:
            current_price = prices[-1]
            distance_pct = ((current_price - indicators.ma_20) / indicators.ma_20) * 100
            # Normalize: -10% = 0, 0% = 50, +10% = 100
            ma_score = max(0, min(100, 50 + (distance_pct * 5)))
            components.append(ma_score)

        # 3. MACD momentum (normalized)
        if indicators.macd_histogram is not None and indicators.ma_20 is not None:
            # Normalize histogram relative to price level
            normalized = (indicators.macd_histogram / indicators.ma_20) * 10000
            macd_score = max(0, min(100, 50 + normalized))
            components.append(macd_score)

        # 4. Volume ratio (>1.5 = greed, <0.5 = fear)
        if indicators.volume_ratio is not None:
            # Normalize: 0.5 = 0, 1.0 = 50, 1.5 = 100
            volume_score = max(0, min(100, (indicators.volume_ratio - 0.5) * 100))
            components.append(volume_score)

        if not components:
            return 50.0  # Neutral if no data

        return sum(components) / len(components)

    def _classify_sentiment(self, fear_greed: float) -> MarketSentiment:
        """Classify sentiment based on fear-greed index.

        Args:
            fear_greed: Fear-Greed index (0-100)

        Returns:
            MarketSentiment classification
        """
        if fear_greed <= 20:
            return MarketSentiment.EXTREME_FEAR
        elif fear_greed <= 40:
            return MarketSentiment.FEAR
        elif fear_greed <= 60:
            return MarketSentiment.NEUTRAL
        elif fear_greed <= 80:
            return MarketSentiment.GREED
        else:
            return MarketSentiment.EXTREME_GREED

    def _generate_recommendation(
        self,
        kospi: MarketState | None,
        kosdaq: MarketState | None,
    ) -> str:
        """Generate market recommendation based on analysis.

        Args:
            kospi: KOSPI market state
            kosdaq: KOSDAQ market state

        Returns:
            Recommendation text in Korean
        """
        if kospi is None and kosdaq is None:
            return "분석 데이터가 부족합니다. 지수 가격 데이터를 먼저 수집해주세요."

        recommendations: list[str] = []

        # Analyze primary market (KOSPI)
        primary = kospi if kospi else kosdaq
        if primary:
            if primary.sentiment == MarketSentiment.EXTREME_FEAR:
                recommendations.append(
                    "시장이 극도의 공포 구간에 있습니다. 역발상 매수 기회를 모색할 수 있습니다."
                )
            elif primary.sentiment == MarketSentiment.FEAR:
                recommendations.append(
                    "시장 심리가 위축되어 있습니다. 신중한 종목 선별이 필요합니다."
                )
            elif primary.sentiment == MarketSentiment.GREED:
                recommendations.append("시장 심리가 과열되고 있습니다. 리스크 관리에 주의하세요.")
            elif primary.sentiment == MarketSentiment.EXTREME_GREED:
                recommendations.append("시장이 과열 구간입니다. 차익 실현을 고려하세요.")
            else:
                recommendations.append("시장이 중립적인 상태입니다.")

            if primary.trend == MarketTrend.UPTREND:
                recommendations.append(f"{primary.index_code} 지수가 상승 추세입니다.")
            elif primary.trend == MarketTrend.DOWNTREND:
                recommendations.append(f"{primary.index_code} 지수가 하락 추세입니다.")
            else:
                recommendations.append(f"{primary.index_code} 지수가 횡보 중입니다.")

        # Add RSI insight if available
        if primary and primary.indicators.rsi_14:
            rsi = primary.indicators.rsi_14
            if rsi < 30:
                recommendations.append(f"RSI({rsi:.1f})가 과매도 구간입니다.")
            elif rsi > 70:
                recommendations.append(f"RSI({rsi:.1f})가 과매수 구간입니다.")

        return " ".join(recommendations)

    async def get_stock_market_state(
        self,
        stock_code: str,
        target_date: date | None = None,
    ) -> MarketState | None:
        """Analyze individual stock's market state.

        Args:
            stock_code: Stock code to analyze
            target_date: Target date for analysis

        Returns:
            MarketState for the stock or None if insufficient data
        """
        if target_date is None:
            target_date = date.today()

        return await self._analyze_index(stock_code, target_date)
