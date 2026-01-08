"""Technical Indicator Calculator for BNF-style swing trading.

This module provides technical indicator calculations used by the AI signal generator.
Includes RSI, MACD, Bollinger Bands, SMA, EMA, and volume spike detection.
"""

import math

import numpy as np


class IndicatorCalculator:
    """Technical indicator calculator for trading signals.

    Provides methods to calculate various technical indicators used in
    BNF-style swing trading strategy:
    - SMA/EMA for trend analysis
    - RSI for overbought/oversold detection
    - MACD for momentum
    - Bollinger Bands for volatility
    - Volume spike detection
    - Golden/Death cross detection
    """

    def _validate_period(self, period: int) -> None:
        """Validate that period is positive."""
        if period <= 0:
            raise ValueError(f"Period must be positive, got {period}")

    def calculate_sma(self, prices: list[float], period: int) -> list[float]:
        """Calculate Simple Moving Average.

        Args:
            prices: List of price values
            period: Number of periods for the moving average

        Returns:
            List of SMA values (NaN for indices before period is complete)
        """
        self._validate_period(period)

        if not prices:
            return []

        result: list[float] = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(math.nan)
            else:
                window = prices[i - period + 1 : i + 1]
                result.append(sum(window) / period)

        return result

    def calculate_ema(self, prices: list[float], period: int) -> list[float]:
        """Calculate Exponential Moving Average.

        Uses SMA for the first EMA value, then applies exponential weighting.

        Args:
            prices: List of price values
            period: Number of periods for the moving average

        Returns:
            List of EMA values (NaN for indices before period is complete)
        """
        self._validate_period(period)

        if not prices:
            return []

        result: list[float] = []
        multiplier = 2.0 / (period + 1)

        for i in range(len(prices)):
            if i < period - 1:
                result.append(math.nan)
            elif i == period - 1:
                # First EMA is SMA
                sma = sum(prices[:period]) / period
                result.append(sma)
            else:
                # EMA = (Price * multiplier) + (Previous EMA * (1 - multiplier))
                ema = (prices[i] * multiplier) + (result[i - 1] * (1 - multiplier))
                result.append(ema)

        return result

    def calculate_rsi(self, prices: list[float], period: int = 14) -> list[float]:
        """Calculate Relative Strength Index.

        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

        Args:
            prices: List of price values
            period: RSI period (default: 14)

        Returns:
            List of RSI values (NaN for indices before enough data)
        """
        self._validate_period(period)

        if not prices or len(prices) < 2:
            return [math.nan] * len(prices) if prices else []

        # Calculate price changes
        changes = [0.0] + [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        result: list[float] = []

        for i in range(len(prices)):
            if i < period:
                result.append(math.nan)
            elif i == period:
                # First RSI calculation using simple average
                avg_gain = sum(gains[1 : period + 1]) / period
                avg_loss = sum(losses[1 : period + 1]) / period

                if avg_loss == 0:
                    if avg_gain == 0:
                        result.append(math.nan)
                    else:
                        result.append(100.0)
                else:
                    rs = avg_gain / avg_loss
                    result.append(100.0 - (100.0 / (1.0 + rs)))
            else:
                # Subsequent RSI using smoothed average (Wilder's smoothing)
                prev_rsi_idx = i - 1
                if math.isnan(result[prev_rsi_idx]):
                    result.append(math.nan)
                    continue

                # Calculate smoothed averages
                prev_avg_gain = sum(gains[i - period + 1 : i]) / period
                prev_avg_loss = sum(losses[i - period + 1 : i]) / period

                # Wilder's smoothing method
                avg_gain = ((prev_avg_gain * (period - 1)) + gains[i]) / period
                avg_loss = ((prev_avg_loss * (period - 1)) + losses[i]) / period

                if avg_loss == 0:
                    if avg_gain == 0:
                        result.append(math.nan)
                    else:
                        result.append(100.0)
                else:
                    rs = avg_gain / avg_loss
                    result.append(100.0 - (100.0 / (1.0 + rs)))

        return result

    def calculate_macd(
        self,
        prices: list[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[list[float], list[float], list[float]]:
        """Calculate MACD (Moving Average Convergence Divergence).

        MACD Line = Fast EMA - Slow EMA
        Signal Line = EMA of MACD Line
        Histogram = MACD Line - Signal Line

        Args:
            prices: List of price values
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line EMA period (default: 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        if not prices:
            return [], [], []

        fast_ema = self.calculate_ema(prices, fast)
        slow_ema = self.calculate_ema(prices, slow)

        # MACD Line
        macd_line: list[float] = []
        for i in range(len(prices)):
            if math.isnan(fast_ema[i]) or math.isnan(slow_ema[i]):
                macd_line.append(math.nan)
            else:
                macd_line.append(fast_ema[i] - slow_ema[i])

        # Signal Line (EMA of MACD Line)
        # Need to handle NaN values properly
        valid_macd_start = slow - 1  # First valid MACD index

        signal_line: list[float] = []
        multiplier = 2.0 / (signal + 1)

        for i in range(len(prices)):
            if i < valid_macd_start + signal - 1:
                signal_line.append(math.nan)
            elif i == valid_macd_start + signal - 1:
                # First signal is SMA of first 'signal' valid MACD values
                valid_macd = macd_line[valid_macd_start : valid_macd_start + signal]
                signal_line.append(sum(valid_macd) / signal)
            else:
                # EMA of MACD
                prev_signal = signal_line[i - 1]
                if math.isnan(prev_signal) or math.isnan(macd_line[i]):
                    signal_line.append(math.nan)
                else:
                    ema = (macd_line[i] * multiplier) + (prev_signal * (1 - multiplier))
                    signal_line.append(ema)

        # Histogram
        histogram: list[float] = []
        for i in range(len(prices)):
            if math.isnan(macd_line[i]) or math.isnan(signal_line[i]):
                histogram.append(math.nan)
            else:
                histogram.append(macd_line[i] - signal_line[i])

        return macd_line, signal_line, histogram

    def calculate_bollinger_bands(
        self,
        prices: list[float],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple[list[float], list[float], list[float]]:
        """Calculate Bollinger Bands.

        Middle Band = SMA
        Upper Band = Middle Band + (std_dev * Standard Deviation)
        Lower Band = Middle Band - (std_dev * Standard Deviation)

        Args:
            prices: List of price values
            period: SMA period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)

        Returns:
            Tuple of (upper, middle, lower) bands
        """
        if not prices:
            return [], [], []

        middle = self.calculate_sma(prices, period)

        upper: list[float] = []
        lower: list[float] = []

        for i in range(len(prices)):
            if i < period - 1:
                upper.append(math.nan)
                lower.append(math.nan)
            else:
                window = prices[i - period + 1 : i + 1]
                std = float(np.std(window, ddof=0))
                upper.append(middle[i] + (std_dev * std))
                lower.append(middle[i] - (std_dev * std))

        return upper, middle, lower

    def calculate_volume_spike(
        self, volumes: list[float], threshold: float = 2.0, lookback: int = 20
    ) -> list[bool]:
        """Detect volume spikes.

        A spike is detected when current volume exceeds the average
        of previous periods by the threshold multiplier.

        Args:
            volumes: List of volume values
            threshold: Multiplier for spike detection (default: 2.0)
            lookback: Number of periods for average calculation (default: 20)

        Returns:
            List of boolean values indicating spike presence
        """
        if not volumes:
            return []

        result: list[bool] = []

        for i in range(len(volumes)):
            if i < lookback - 1:
                # Not enough history, use available data
                if i == 0:
                    result.append(False)
                else:
                    avg = sum(volumes[:i]) / i
                    result.append(volumes[i] >= avg * threshold)
            else:
                avg = sum(volumes[i - lookback + 1 : i]) / (lookback - 1)
                result.append(volumes[i] >= avg * threshold)

        return result

    def detect_golden_cross(
        self, prices: list[float], short_period: int = 5, long_period: int = 20
    ) -> bool:
        """Detect Golden Cross.

        Golden Cross occurs when short-term MA crosses above long-term MA.

        Args:
            prices: List of price values
            short_period: Short MA period (default: 5)
            long_period: Long MA period (default: 20)

        Returns:
            True if golden cross detected at the latest data point
        """
        if len(prices) < long_period + 1:
            return False

        short_ma = self.calculate_sma(prices, short_period)
        long_ma = self.calculate_sma(prices, long_period)

        # Check if short MA crossed above long MA
        # Current: short > long, Previous: short <= long
        curr_idx = len(prices) - 1
        prev_idx = curr_idx - 1

        if (
            math.isnan(short_ma[curr_idx])
            or math.isnan(long_ma[curr_idx])
            or math.isnan(short_ma[prev_idx])
            or math.isnan(long_ma[prev_idx])
        ):
            return False

        curr_short_above = short_ma[curr_idx] > long_ma[curr_idx]
        prev_short_above = short_ma[prev_idx] > long_ma[prev_idx]

        return curr_short_above and not prev_short_above

    def detect_death_cross(
        self, prices: list[float], short_period: int = 5, long_period: int = 20
    ) -> bool:
        """Detect Death Cross.

        Death Cross occurs when short-term MA crosses below long-term MA.

        Args:
            prices: List of price values
            short_period: Short MA period (default: 5)
            long_period: Long MA period (default: 20)

        Returns:
            True if death cross detected at the latest data point
        """
        if len(prices) < long_period + 1:
            return False

        short_ma = self.calculate_sma(prices, short_period)
        long_ma = self.calculate_sma(prices, long_period)

        # Check if short MA crossed below long MA
        # Current: short < long, Previous: short >= long
        curr_idx = len(prices) - 1
        prev_idx = curr_idx - 1

        if (
            math.isnan(short_ma[curr_idx])
            or math.isnan(long_ma[curr_idx])
            or math.isnan(short_ma[prev_idx])
            or math.isnan(long_ma[prev_idx])
        ):
            return False

        curr_short_below = short_ma[curr_idx] < long_ma[curr_idx]
        prev_short_below = short_ma[prev_idx] < long_ma[prev_idx]

        return curr_short_below and not prev_short_below

    # BNF Strategy Helper Methods

    def is_oversold(self, prices: list[float], period: int = 14, threshold: float = 30) -> bool:
        """Check if RSI indicates oversold condition.

        Args:
            prices: List of price values
            period: RSI period
            threshold: RSI threshold for oversold (default: 30)

        Returns:
            True if current RSI is below threshold
        """
        if len(prices) < period + 1:
            return False

        rsi = self.calculate_rsi(prices, period)
        last_rsi = rsi[-1]

        if math.isnan(last_rsi):
            return False

        return last_rsi < threshold

    def is_overbought(self, prices: list[float], period: int = 14, threshold: float = 70) -> bool:
        """Check if RSI indicates overbought condition.

        Args:
            prices: List of price values
            period: RSI period
            threshold: RSI threshold for overbought (default: 70)

        Returns:
            True if current RSI is above threshold
        """
        if len(prices) < period + 1:
            return False

        rsi = self.calculate_rsi(prices, period)
        last_rsi = rsi[-1]

        if math.isnan(last_rsi):
            return False

        return last_rsi > threshold

    def is_below_lower_band(
        self, prices: list[float], period: int = 20, std_dev: float = 2.0
    ) -> bool:
        """Check if current price is below lower Bollinger Band.

        Args:
            prices: List of price values
            period: Bollinger Band period
            std_dev: Standard deviation multiplier

        Returns:
            True if last price is below lower band
        """
        if len(prices) < period:
            return False

        _, _, lower = self.calculate_bollinger_bands(prices, period, std_dev)
        last_lower = lower[-1]

        if math.isnan(last_lower):
            return False

        return prices[-1] < last_lower

    def is_above_upper_band(
        self, prices: list[float], period: int = 20, std_dev: float = 2.0
    ) -> bool:
        """Check if current price is above upper Bollinger Band.

        Args:
            prices: List of price values
            period: Bollinger Band period
            std_dev: Standard deviation multiplier

        Returns:
            True if last price is above upper band
        """
        if len(prices) < period:
            return False

        upper, _, _ = self.calculate_bollinger_bands(prices, period, std_dev)
        last_upper = upper[-1]

        if math.isnan(last_upper):
            return False

        return prices[-1] > last_upper
