"""BNF-style contrarian swing trading strategy.

This module implements the BNF (Big-Name Fund) style trading strategy
that focuses on buying oversold stocks and selling overbought stocks.

BNF Strategy Rules:
- BUY: RSI < 30 (oversold) + volume spike + below lower Bollinger band
- SELL: RSI > 70 (overbought) + volume decrease + above upper Bollinger band
- Golden/Death cross confirmation via 5/20 MA
"""

import math
from typing import Any


class BNFStrategy:
    """BNF-style contrarian swing trading strategy.

    This strategy identifies potential reversal points by detecting
    extreme market conditions:
    - Oversold conditions for buying opportunities
    - Overbought conditions for selling opportunities
    """

    # Strategy thresholds
    RSI_OVERSOLD_THRESHOLD = 30.0
    RSI_OVERBOUGHT_THRESHOLD = 70.0
    RSI_EXTREME_OVERSOLD = 20.0
    RSI_EXTREME_OVERBOUGHT = 80.0

    # Confidence weights
    BASE_CONFIDENCE = 0.3
    RSI_WEIGHT = 0.35
    VOLUME_WEIGHT = 0.25
    BOLLINGER_WEIGHT = 0.25
    CROSS_WEIGHT = 0.15

    def check_buy_signal(
        self, indicators: dict[str, Any]
    ) -> tuple[bool, float, str]:
        """Check for buy signal based on BNF strategy rules.

        Buy signal conditions:
        - RSI < 30 (oversold)
        - Volume spike present (current volume >= 2x average)
        - Price below lower Bollinger band

        Args:
            indicators: Dictionary containing calculated indicators:
                - rsi: RSI value
                - volume_spike: bool indicating volume spike
                - below_lower_band: bool indicating below lower Bollinger band
                - golden_cross: bool indicating golden cross detected
                - death_cross: bool indicating death cross detected
                - macd_histogram: MACD histogram value

        Returns:
            Tuple of (is_buy, confidence, reason)
            - is_buy: True if buy signal is triggered
            - confidence: Signal confidence (0.0 to 1.0)
            - reason: Human-readable reason for the signal
        """
        rsi = indicators.get("rsi", 50.0)
        volume_spike = indicators.get("volume_spike", False)
        below_lower_band = indicators.get("below_lower_band", False)
        golden_cross = indicators.get("golden_cross", False)

        # Handle NaN RSI
        if math.isnan(rsi):
            return False, 0.0, "RSI is not available"

        conditions_met: list[str] = []
        confidence = 0.0

        # Check RSI oversold condition
        rsi_oversold = rsi < self.RSI_OVERSOLD_THRESHOLD
        if rsi_oversold:
            # Scale confidence based on how oversold
            rsi_score = (self.RSI_OVERSOLD_THRESHOLD - rsi) / self.RSI_OVERSOLD_THRESHOLD
            rsi_score = min(1.0, rsi_score * 1.5)  # Boost for extreme oversold
            confidence += self.RSI_WEIGHT * rsi_score
            conditions_met.append(f"RSI oversold ({rsi:.1f})")

        # Check volume spike condition
        if volume_spike:
            confidence += self.VOLUME_WEIGHT
            conditions_met.append("Volume spike detected")

        # Check Bollinger band condition
        if below_lower_band:
            confidence += self.BOLLINGER_WEIGHT
            conditions_met.append("Below Bollinger lower band")

        # Golden cross boost
        if golden_cross:
            confidence += self.CROSS_WEIGHT
            conditions_met.append("Golden cross confirmed")

        # Determine if buy signal should be triggered
        # Need RSI oversold AND at least one other condition
        is_buy = rsi_oversold and (volume_spike or below_lower_band)

        # Normalize confidence
        max_confidence = (
            self.RSI_WEIGHT + self.VOLUME_WEIGHT + self.BOLLINGER_WEIGHT + self.CROSS_WEIGHT
        )
        confidence = min(1.0, confidence / max_confidence) if max_confidence > 0 else 0.0

        # Ensure minimum confidence when signal is triggered
        if is_buy and confidence < 0.5:
            confidence = 0.5

        # Build reason string
        if conditions_met:
            reason = "BUY signal: " + ", ".join(conditions_met)
        else:
            reason = "No buy conditions met"

        return is_buy, confidence, reason

    def check_sell_signal(
        self, indicators: dict[str, Any]
    ) -> tuple[bool, float, str]:
        """Check for sell signal based on BNF strategy rules.

        Sell signal conditions:
        - RSI > 70 (overbought)
        - Volume decrease (no volume spike)
        - Price above upper Bollinger band

        Args:
            indicators: Dictionary containing calculated indicators:
                - rsi: RSI value
                - volume_spike: bool indicating volume spike
                - above_upper_band: bool indicating above upper Bollinger band
                - golden_cross: bool indicating golden cross detected
                - death_cross: bool indicating death cross detected
                - macd_histogram: MACD histogram value

        Returns:
            Tuple of (is_sell, confidence, reason)
            - is_sell: True if sell signal is triggered
            - confidence: Signal confidence (0.0 to 1.0)
            - reason: Human-readable reason for the signal
        """
        rsi = indicators.get("rsi", 50.0)
        volume_spike = indicators.get("volume_spike", True)  # Default to spike (no decrease)
        above_upper_band = indicators.get("above_upper_band", False)
        death_cross = indicators.get("death_cross", False)

        # Handle NaN RSI
        if math.isnan(rsi):
            return False, 0.0, "RSI is not available"

        conditions_met: list[str] = []
        confidence = 0.0

        # Check RSI overbought condition
        rsi_overbought = rsi > self.RSI_OVERBOUGHT_THRESHOLD
        if rsi_overbought:
            # Scale confidence based on how overbought
            rsi_score = (rsi - self.RSI_OVERBOUGHT_THRESHOLD) / (100 - self.RSI_OVERBOUGHT_THRESHOLD)
            rsi_score = min(1.0, rsi_score * 1.5)  # Boost for extreme overbought
            confidence += self.RSI_WEIGHT * rsi_score
            conditions_met.append(f"RSI overbought ({rsi:.1f})")

        # Check volume decrease condition (no spike = decreasing volume)
        volume_decrease = not volume_spike
        if volume_decrease:
            confidence += self.VOLUME_WEIGHT
            conditions_met.append("Volume decreasing")

        # Check Bollinger band condition
        if above_upper_band:
            confidence += self.BOLLINGER_WEIGHT
            conditions_met.append("Above Bollinger upper band")

        # Death cross boost
        if death_cross:
            confidence += self.CROSS_WEIGHT
            conditions_met.append("Death cross confirmed")

        # Determine if sell signal should be triggered
        # Need RSI overbought AND at least one other condition
        is_sell = rsi_overbought and (volume_decrease or above_upper_band)

        # Normalize confidence
        max_confidence = (
            self.RSI_WEIGHT + self.VOLUME_WEIGHT + self.BOLLINGER_WEIGHT + self.CROSS_WEIGHT
        )
        confidence = min(1.0, confidence / max_confidence) if max_confidence > 0 else 0.0

        # Ensure minimum confidence when signal is triggered
        if is_sell and confidence < 0.5:
            confidence = 0.5

        # Build reason string
        if conditions_met:
            reason = "SELL signal: " + ", ".join(conditions_met)
        else:
            reason = "No sell conditions met"

        return is_sell, confidence, reason

    def check_golden_cross(self, indicators: dict[str, Any]) -> bool:
        """Check if golden cross is indicated in the indicators.

        Golden Cross occurs when short-term MA crosses above long-term MA,
        indicating bullish momentum.

        Args:
            indicators: Dictionary containing golden_cross indicator

        Returns:
            True if golden cross is detected
        """
        return indicators.get("golden_cross", False)

    def check_death_cross(self, indicators: dict[str, Any]) -> bool:
        """Check if death cross is indicated in the indicators.

        Death Cross occurs when short-term MA crosses below long-term MA,
        indicating bearish momentum.

        Args:
            indicators: Dictionary containing death_cross indicator

        Returns:
            True if death cross is detected
        """
        return indicators.get("death_cross", False)
