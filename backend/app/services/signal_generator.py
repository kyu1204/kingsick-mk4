"""AI-based trading signal generator.

This module provides the SignalGenerator class that combines technical
indicators with the BNF strategy to generate trading signals.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.ai.bnf_strategy import BNFStrategy
from app.services.indicator import IndicatorCalculator


class SignalType(Enum):
    """Trading signal types."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """Trading signal with confidence and reasoning.

    Attributes:
        signal: The signal type (BUY, SELL, or HOLD)
        confidence: Signal confidence score (0.0 to 1.0)
        reason: Human-readable explanation for the signal
        indicators: Dictionary of calculated indicator values
    """

    signal: SignalType
    confidence: float
    reason: str
    indicators: dict[str, Any]


class SignalGenerator:
    """AI-based trading signal generator using BNF strategy.

    Combines technical indicator calculations with BNF-style contrarian
    swing trading strategy to generate actionable trading signals.
    """

    # Minimum data points required for reliable signals
    MIN_DATA_POINTS = 30

    # RSI period for signal generation
    RSI_PERIOD = 14

    # Bollinger Bands parameters
    BOLLINGER_PERIOD = 20
    BOLLINGER_STD_DEV = 2.0

    # Volume spike parameters
    VOLUME_SPIKE_THRESHOLD = 2.0
    VOLUME_LOOKBACK = 20

    # Moving average periods for cross detection
    SHORT_MA_PERIOD = 5
    LONG_MA_PERIOD = 20

    def __init__(
        self,
        indicator_calculator: IndicatorCalculator,
        strategy: BNFStrategy,
    ) -> None:
        """Initialize the signal generator.

        Args:
            indicator_calculator: IndicatorCalculator instance for technical analysis
            strategy: BNFStrategy instance for signal rules
        """
        self.indicator_calculator = indicator_calculator
        self.strategy = strategy

    def generate_signal(
        self,
        prices: list[float],
        volumes: list[float],
    ) -> TradingSignal:
        """Generate a trading signal based on price and volume data.

        Process:
        1. Calculate technical indicators (RSI, MACD, Bollinger, etc.)
        2. Apply BNF strategy rules
        3. Calculate signal confidence
        4. Return TradingSignal with all details

        Args:
            prices: List of historical price values (oldest to newest)
            volumes: List of historical volume values (oldest to newest)

        Returns:
            TradingSignal with signal type, confidence, reason, and indicators
        """
        # Handle empty or insufficient data
        if not prices or len(prices) < 2:
            return TradingSignal(
                signal=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for signal generation",
                indicators={},
            )

        # Handle mismatched data lengths
        min_length = min(len(prices), len(volumes)) if volumes else len(prices)
        prices = prices[:min_length]
        volumes = volumes[:min_length] if volumes else [0.0] * min_length

        # Check for minimum data requirements
        if len(prices) < self.MIN_DATA_POINTS:
            return TradingSignal(
                signal=SignalType.HOLD,
                confidence=0.0,
                reason=f"Insufficient data (need at least {self.MIN_DATA_POINTS} points)",
                indicators={"data_points": len(prices)},
            )

        # Calculate all technical indicators
        indicators = self._calculate_indicators(prices, volumes)

        # Check for buy signal
        is_buy, buy_confidence, buy_reason = self.strategy.check_buy_signal(indicators)

        # Check for sell signal
        is_sell, sell_confidence, sell_reason = self.strategy.check_sell_signal(indicators)

        # Determine final signal
        if is_buy and not is_sell:
            return TradingSignal(
                signal=SignalType.BUY,
                confidence=buy_confidence,
                reason=buy_reason,
                indicators=indicators,
            )
        elif is_sell and not is_buy:
            return TradingSignal(
                signal=SignalType.SELL,
                confidence=sell_confidence,
                reason=sell_reason,
                indicators=indicators,
            )
        elif is_buy and is_sell:
            # Conflicting signals - choose the stronger one
            if buy_confidence > sell_confidence:
                return TradingSignal(
                    signal=SignalType.BUY,
                    confidence=buy_confidence * 0.8,  # Reduce confidence due to conflict
                    reason=f"{buy_reason} (conflicting sell signal)",
                    indicators=indicators,
                )
            elif sell_confidence > buy_confidence:
                return TradingSignal(
                    signal=SignalType.SELL,
                    confidence=sell_confidence * 0.8,
                    reason=f"{sell_reason} (conflicting buy signal)",
                    indicators=indicators,
                )
            else:
                # Equal confidence - hold
                return TradingSignal(
                    signal=SignalType.HOLD,
                    confidence=0.5,
                    reason="Conflicting buy/sell signals with equal strength",
                    indicators=indicators,
                )
        else:
            # No signal - hold
            return TradingSignal(
                signal=SignalType.HOLD,
                confidence=0.5,
                reason="Market conditions neutral - no clear signal",
                indicators=indicators,
            )

    def _calculate_indicators(
        self,
        prices: list[float],
        volumes: list[float],
    ) -> dict[str, Any]:
        """Calculate all technical indicators.

        Args:
            prices: Historical price data
            volumes: Historical volume data

        Returns:
            Dictionary containing all calculated indicators
        """
        indicators: dict[str, Any] = {}

        # Calculate RSI
        rsi_values = self.indicator_calculator.calculate_rsi(prices, self.RSI_PERIOD)
        indicators["rsi"] = rsi_values[-1] if rsi_values and not math.isnan(rsi_values[-1]) else math.nan

        # Calculate MACD
        macd_line, signal_line, histogram = self.indicator_calculator.calculate_macd(prices)
        if histogram and len(histogram) > 0:
            indicators["macd_line"] = macd_line[-1] if not math.isnan(macd_line[-1]) else 0.0
            indicators["macd_signal"] = signal_line[-1] if not math.isnan(signal_line[-1]) else 0.0
            indicators["macd_histogram"] = histogram[-1] if not math.isnan(histogram[-1]) else 0.0
        else:
            indicators["macd_line"] = 0.0
            indicators["macd_signal"] = 0.0
            indicators["macd_histogram"] = 0.0

        # Calculate Bollinger Bands
        upper, middle, lower = self.indicator_calculator.calculate_bollinger_bands(
            prices, self.BOLLINGER_PERIOD, self.BOLLINGER_STD_DEV
        )
        if upper and middle and lower:
            indicators["bollinger_upper"] = upper[-1] if not math.isnan(upper[-1]) else 0.0
            indicators["bollinger_middle"] = middle[-1] if not math.isnan(middle[-1]) else 0.0
            indicators["bollinger_lower"] = lower[-1] if not math.isnan(lower[-1]) else 0.0

            current_price = prices[-1]
            indicators["below_lower_band"] = current_price < lower[-1] if not math.isnan(lower[-1]) else False
            indicators["above_upper_band"] = current_price > upper[-1] if not math.isnan(upper[-1]) else False
        else:
            indicators["bollinger_upper"] = 0.0
            indicators["bollinger_middle"] = 0.0
            indicators["bollinger_lower"] = 0.0
            indicators["below_lower_band"] = False
            indicators["above_upper_band"] = False

        # Calculate volume spike
        volume_spikes = self.indicator_calculator.calculate_volume_spike(
            volumes, self.VOLUME_SPIKE_THRESHOLD, self.VOLUME_LOOKBACK
        )
        indicators["volume_spike"] = volume_spikes[-1] if volume_spikes else False

        # Detect golden/death cross
        indicators["golden_cross"] = self.indicator_calculator.detect_golden_cross(
            prices, self.SHORT_MA_PERIOD, self.LONG_MA_PERIOD
        )
        indicators["death_cross"] = self.indicator_calculator.detect_death_cross(
            prices, self.SHORT_MA_PERIOD, self.LONG_MA_PERIOD
        )

        # Store current price
        indicators["current_price"] = prices[-1]

        return indicators

    def calculate_confidence(
        self,
        buy_conditions: list[bool],
        sell_conditions: list[bool],
    ) -> float:
        """Calculate signal confidence based on condition fulfillment.

        The confidence is calculated as the ratio of conditions met,
        with adjustment for conflicting signals.

        Args:
            buy_conditions: List of boolean buy conditions
            sell_conditions: List of boolean sell conditions

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not buy_conditions and not sell_conditions:
            return 0.0

        buy_count = sum(buy_conditions) if buy_conditions else 0
        sell_count = sum(sell_conditions) if sell_conditions else 0

        buy_total = len(buy_conditions) if buy_conditions else 1
        sell_total = len(sell_conditions) if sell_conditions else 1

        buy_ratio = buy_count / buy_total
        sell_ratio = sell_count / sell_total

        # If both have conditions met, reduce confidence
        if buy_count > 0 and sell_count > 0:
            # Conflicting signals reduce overall confidence
            dominant_ratio = max(buy_ratio, sell_ratio)
            subordinate_ratio = min(buy_ratio, sell_ratio)
            confidence = dominant_ratio * (1 - subordinate_ratio * 0.5)
        else:
            # No conflict - use the ratio of met conditions
            confidence = max(buy_ratio, sell_ratio)

        return min(1.0, max(0.0, confidence))
