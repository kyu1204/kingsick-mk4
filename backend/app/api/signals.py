"""
API router for AI signal generation.

Provides endpoints for generating trading signals based on
technical indicators and BNF strategy.
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.bnf_strategy import BNFStrategy
from app.api.schemas import (
    GenerateSignalRequest,
    SignalTypeEnum,
    TradingSignalResponse,
)
from app.services.indicator import IndicatorCalculator
from app.services.signal_generator import SignalGenerator, SignalType

router = APIRouter(prefix="/signals", tags=["signals"])


def get_signal_generator() -> SignalGenerator:
    """Dependency to get SignalGenerator instance."""
    indicator_calculator = IndicatorCalculator()
    strategy = BNFStrategy()
    return SignalGenerator(indicator_calculator, strategy)


def _convert_nan_to_serializable(indicators: dict) -> dict:
    """Convert NaN values in indicators to None for JSON serialization."""
    result = {}
    for key, value in indicators.items():
        if isinstance(value, float) and math.isnan(value):
            result[key] = None
        else:
            result[key] = value
    return result


def _signal_type_to_enum(signal_type: SignalType) -> SignalTypeEnum:
    """Convert SignalType to SignalTypeEnum."""
    if signal_type == SignalType.BUY:
        return SignalTypeEnum.BUY
    elif signal_type == SignalType.SELL:
        return SignalTypeEnum.SELL
    else:
        return SignalTypeEnum.HOLD


@router.post("/generate", response_model=TradingSignalResponse)
def generate_signal(
    request: GenerateSignalRequest,
    generator: Annotated[SignalGenerator, Depends(get_signal_generator)],
) -> TradingSignalResponse:
    """
    Generate a trading signal based on price and volume data.

    Uses BNF strategy rules with technical indicators:
    - RSI for overbought/oversold detection
    - MACD for momentum
    - Bollinger Bands for volatility
    - Volume spike detection
    - Golden/Death cross confirmation

    Args:
        request: GenerateSignalRequest with prices and volumes
        generator: SignalGenerator instance

    Returns:
        TradingSignalResponse with signal type, confidence, reason, and indicators
    """
    signal = generator.generate_signal(request.prices, request.volumes)

    return TradingSignalResponse(
        signal=_signal_type_to_enum(signal.signal),
        confidence=signal.confidence,
        reason=signal.reason,
        indicators=_convert_nan_to_serializable(signal.indicators),
    )
