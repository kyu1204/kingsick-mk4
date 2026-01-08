"""
API router for technical indicator calculations.

Provides endpoints for calculating various technical indicators:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume Spike Detection
- Golden/Death Cross Detection
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas import (
    BollingerBandsRequest,
    BollingerBandsResponse,
    CrossDetectionRequest,
    CrossDetectionResponse,
    EMARequest,
    EMAResponse,
    MACDRequest,
    MACDResponse,
    RSIRequest,
    RSIResponse,
    SMARequest,
    SMAResponse,
    VolumeSpikeRequest,
    VolumeSpikeResponse,
)
from app.services.indicator import IndicatorCalculator

router = APIRouter(prefix="/indicators", tags=["indicators"])


def get_indicator_calculator() -> IndicatorCalculator:
    """Dependency to get IndicatorCalculator instance."""
    return IndicatorCalculator()


def _convert_nan_to_none(values: list[float]) -> list[float | None]:
    """Convert NaN values to None for JSON serialization."""
    return [None if math.isnan(v) else v for v in values]


@router.post("/sma", response_model=SMAResponse)
def calculate_sma(
    request: SMARequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> SMAResponse:
    """
    Calculate Simple Moving Average.

    Args:
        request: SMARequest with prices and period
        calculator: IndicatorCalculator instance

    Returns:
        SMAResponse with calculated values
    """
    values = calculator.calculate_sma(request.prices, request.period)
    return SMAResponse(values=_convert_nan_to_none(values))


@router.post("/ema", response_model=EMAResponse)
def calculate_ema(
    request: EMARequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> EMAResponse:
    """
    Calculate Exponential Moving Average.

    Args:
        request: EMARequest with prices and period
        calculator: IndicatorCalculator instance

    Returns:
        EMAResponse with calculated values
    """
    values = calculator.calculate_ema(request.prices, request.period)
    return EMAResponse(values=_convert_nan_to_none(values))


@router.post("/rsi", response_model=RSIResponse)
def calculate_rsi(
    request: RSIRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> RSIResponse:
    """
    Calculate Relative Strength Index.

    Args:
        request: RSIRequest with prices and optional period
        calculator: IndicatorCalculator instance

    Returns:
        RSIResponse with calculated values
    """
    values = calculator.calculate_rsi(request.prices, request.period)
    return RSIResponse(values=_convert_nan_to_none(values))


@router.post("/macd", response_model=MACDResponse)
def calculate_macd(
    request: MACDRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> MACDResponse:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        request: MACDRequest with prices and optional periods
        calculator: IndicatorCalculator instance

    Returns:
        MACDResponse with MACD line, signal line, and histogram
    """
    macd_line, signal_line, histogram = calculator.calculate_macd(
        request.prices, request.fast, request.slow, request.signal
    )
    return MACDResponse(
        macd_line=_convert_nan_to_none(macd_line),
        signal_line=_convert_nan_to_none(signal_line),
        histogram=_convert_nan_to_none(histogram),
    )


@router.post("/bollinger-bands", response_model=BollingerBandsResponse)
def calculate_bollinger_bands(
    request: BollingerBandsRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> BollingerBandsResponse:
    """
    Calculate Bollinger Bands.

    Args:
        request: BollingerBandsRequest with prices, period, and std_dev
        calculator: IndicatorCalculator instance

    Returns:
        BollingerBandsResponse with upper, middle, and lower bands
    """
    upper, middle, lower = calculator.calculate_bollinger_bands(
        request.prices, request.period, request.std_dev
    )
    return BollingerBandsResponse(
        upper=_convert_nan_to_none(upper),
        middle=_convert_nan_to_none(middle),
        lower=_convert_nan_to_none(lower),
    )


@router.post("/volume-spike", response_model=VolumeSpikeResponse)
def detect_volume_spike(
    request: VolumeSpikeRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> VolumeSpikeResponse:
    """
    Detect volume spikes.

    Args:
        request: VolumeSpikeRequest with volumes, threshold, and lookback
        calculator: IndicatorCalculator instance

    Returns:
        VolumeSpikeResponse with spike detection results
    """
    spikes = calculator.calculate_volume_spike(
        request.volumes, request.threshold, request.lookback
    )
    return VolumeSpikeResponse(spikes=spikes)


@router.post("/golden-cross", response_model=CrossDetectionResponse)
def detect_golden_cross(
    request: CrossDetectionRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> CrossDetectionResponse:
    """
    Detect Golden Cross (bullish signal).

    Args:
        request: CrossDetectionRequest with prices and MA periods
        calculator: IndicatorCalculator instance

    Returns:
        CrossDetectionResponse indicating if cross was detected
    """
    detected = calculator.detect_golden_cross(
        request.prices, request.short_period, request.long_period
    )
    return CrossDetectionResponse(detected=detected)


@router.post("/death-cross", response_model=CrossDetectionResponse)
def detect_death_cross(
    request: CrossDetectionRequest,
    calculator: Annotated[IndicatorCalculator, Depends(get_indicator_calculator)],
) -> CrossDetectionResponse:
    """
    Detect Death Cross (bearish signal).

    Args:
        request: CrossDetectionRequest with prices and MA periods
        calculator: IndicatorCalculator instance

    Returns:
        CrossDetectionResponse indicating if cross was detected
    """
    detected = calculator.detect_death_cross(
        request.prices, request.short_period, request.long_period
    )
    return CrossDetectionResponse(detected=detected)
