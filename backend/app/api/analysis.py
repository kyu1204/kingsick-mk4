"""Market Analysis API endpoints.

Provides market state analysis, sector performance, and trading recommendations.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.market_analyzer import (
    InsufficientDataError,
    MarketAnalyzer,
    MarketState,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class MarketIndicatorsResponse(BaseModel):
    """Market indicators response."""

    rsi_14: float | None = None
    ma_5: float | None = None
    ma_20: float | None = None
    ma_60: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    volume_ratio: float | None = None


class MarketStateResponse(BaseModel):
    """Single market state response."""

    index_code: str
    current_price: float
    change_pct: float
    trend: str
    fear_greed_index: float
    sentiment: str
    indicators: MarketIndicatorsResponse
    analysis_date: str


class MarketAnalysisResponse(BaseModel):
    """Full market analysis response."""

    kospi: MarketStateResponse | None = None
    kosdaq: MarketStateResponse | None = None
    recommendation: str
    analysis_date: str


class StockMarketStateResponse(BaseModel):
    """Individual stock market state response."""

    stock_code: str
    current_price: float
    change_pct: float
    trend: str
    fear_greed_index: float
    sentiment: str
    indicators: MarketIndicatorsResponse
    analysis_date: str


def _convert_market_state(state: MarketState) -> MarketStateResponse:
    """Convert MarketState dataclass to response model."""
    return MarketStateResponse(
        index_code=state.index_code,
        current_price=state.current_price,
        change_pct=state.change_pct,
        trend=state.trend.value,
        fear_greed_index=state.fear_greed_index,
        sentiment=state.sentiment.value,
        indicators=MarketIndicatorsResponse(
            rsi_14=state.indicators.rsi_14,
            ma_5=state.indicators.ma_5,
            ma_20=state.indicators.ma_20,
            ma_60=state.indicators.ma_60,
            macd=state.indicators.macd,
            macd_signal=state.indicators.macd_signal,
            macd_histogram=state.indicators.macd_histogram,
            volume_ratio=state.indicators.volume_ratio,
        ),
        analysis_date=state.analysis_date.isoformat(),
    )


@router.get("/market", response_model=MarketAnalysisResponse)
async def get_market_analysis(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    target_date: date | None = None,
) -> MarketAnalysisResponse:
    """Get full market analysis for KOSPI and KOSDAQ.

    Analyzes market conditions including:
    - Trend detection (uptrend/downtrend/sideways)
    - Fear-Greed index (0-100)
    - Technical indicators (RSI, MA, MACD)
    - Trading recommendation

    Args:
        target_date: Optional target date for analysis (default: today)

    Returns:
        MarketAnalysisResponse with KOSPI/KOSDAQ states and recommendation
    """
    analyzer = MarketAnalyzer(db)
    result = await analyzer.analyze_market(target_date)

    return MarketAnalysisResponse(
        kospi=_convert_market_state(result.kospi) if result.kospi else None,
        kosdaq=_convert_market_state(result.kosdaq) if result.kosdaq else None,
        recommendation=result.recommendation,
        analysis_date=result.analysis_date.isoformat(),
    )


@router.get("/market/{index_code}", response_model=MarketStateResponse)
async def get_index_analysis(
    index_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    target_date: date | None = None,
) -> MarketStateResponse:
    """Get analysis for a specific market index.

    Args:
        index_code: Market index code (KOSPI or KOSDAQ)
        target_date: Optional target date for analysis

    Returns:
        MarketStateResponse with index analysis

    Raises:
        404: Insufficient data for analysis
        400: Invalid index code
    """
    valid_indices = ["KOSPI", "KOSDAQ"]
    if index_code.upper() not in valid_indices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid index code. Must be one of: {valid_indices}",
        )

    analyzer = MarketAnalyzer(db)

    try:
        state = await analyzer.analyze_index(index_code.upper(), target_date)
    except InsufficientDataError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return _convert_market_state(state)


@router.get("/stock/{stock_code}/state", response_model=StockMarketStateResponse)
async def get_stock_market_state(
    stock_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    target_date: date | None = None,
) -> StockMarketStateResponse:
    """Get market state analysis for individual stock.

    Analyzes the stock using the same indicators as market analysis:
    - Trend detection
    - Fear-Greed index
    - Technical indicators

    Args:
        stock_code: Stock code to analyze
        target_date: Optional target date for analysis

    Returns:
        StockMarketStateResponse with stock analysis

    Raises:
        404: Insufficient data for analysis
    """
    analyzer = MarketAnalyzer(db)
    state = await analyzer.get_stock_market_state(stock_code, target_date)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for stock {stock_code}. Need at least 60 days of price data.",
        )

    return StockMarketStateResponse(
        stock_code=state.index_code,
        current_price=state.current_price,
        change_pct=state.change_pct,
        trend=state.trend.value,
        fear_greed_index=state.fear_greed_index,
        sentiment=state.sentiment.value,
        indicators=MarketIndicatorsResponse(
            rsi_14=state.indicators.rsi_14,
            ma_5=state.indicators.ma_5,
            ma_20=state.indicators.ma_20,
            ma_60=state.indicators.ma_60,
            macd=state.indicators.macd,
            macd_signal=state.indicators.macd_signal,
            macd_histogram=state.indicators.macd_histogram,
            volume_ratio=state.indicators.volume_ratio,
        ),
        analysis_date=state.analysis_date.isoformat(),
    )
