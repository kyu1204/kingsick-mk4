"""Unit tests for IndicatorCalculator.

Tests for technical indicator calculations used in BNF-style swing trading.
Target coverage: 95%+
"""

import pytest

from app.services.indicator import IndicatorCalculator


class TestSMA:
    """Tests for Simple Moving Average calculation."""

    def test_sma_calculation(self):
        """SMA should calculate the correct arithmetic mean over the period."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = calc.calculate_sma(prices, period=3)

        # SMA(3) for [10, 20, 30, 40, 50]:
        # Index 0, 1: Not enough data
        # Index 2: (10 + 20 + 30) / 3 = 20.0
        # Index 3: (20 + 30 + 40) / 3 = 30.0
        # Index 4: (30 + 40 + 50) / 3 = 40.0
        assert len(result) == 5
        assert result[2] == pytest.approx(20.0)
        assert result[3] == pytest.approx(30.0)
        assert result[4] == pytest.approx(40.0)

    def test_sma_with_insufficient_data(self):
        """SMA should return NaN for indices before the period is complete."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.calculate_sma(prices, period=3)

        import math
        assert math.isnan(result[0])
        assert math.isnan(result[1])
        assert result[2] == pytest.approx(20.0)

    def test_sma_single_period(self):
        """SMA with period=1 should return the same prices."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.calculate_sma(prices, period=1)

        assert result[0] == pytest.approx(10.0)
        assert result[1] == pytest.approx(20.0)
        assert result[2] == pytest.approx(30.0)

    def test_sma_empty_list(self):
        """SMA should handle empty price list."""
        calc = IndicatorCalculator()

        result = calc.calculate_sma([], period=3)

        assert result == []


class TestEMA:
    """Tests for Exponential Moving Average calculation."""

    def test_ema_calculation(self):
        """EMA should calculate correctly with exponential weighting."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = calc.calculate_ema(prices, period=3)

        # EMA calculation with multiplier = 2 / (period + 1) = 2/4 = 0.5
        # First EMA = SMA of first 3 values = (10 + 20 + 30) / 3 = 20
        # EMA[3] = 40 * 0.5 + 20 * 0.5 = 30
        # EMA[4] = 50 * 0.5 + 30 * 0.5 = 40
        assert len(result) == 5
        assert result[2] == pytest.approx(20.0)  # First EMA = SMA
        assert result[3] == pytest.approx(30.0)
        assert result[4] == pytest.approx(40.0)

    def test_ema_with_insufficient_data(self):
        """EMA should return NaN for indices before the period is complete."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.calculate_ema(prices, period=3)

        import math
        assert math.isnan(result[0])
        assert math.isnan(result[1])
        assert result[2] == pytest.approx(20.0)

    def test_ema_empty_list(self):
        """EMA should handle empty price list."""
        calc = IndicatorCalculator()

        result = calc.calculate_ema([], period=3)

        assert result == []


class TestRSI:
    """Tests for Relative Strength Index calculation."""

    def test_rsi_calculation(self):
        """RSI should be calculated correctly."""
        calc = IndicatorCalculator()
        # Prices that go up more than down should have RSI > 50
        prices = [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]

        result = calc.calculate_rsi(prices, period=14)

        # After 14 periods, RSI should be calculated
        assert len(result) == len(prices)
        # RSI should be between 0 and 100
        for i in range(14, len(result)):
            assert 0 <= result[i] <= 100

    def test_rsi_oversold_detection(self):
        """RSI below 30 indicates oversold condition."""
        calc = IndicatorCalculator()
        # Create strongly declining prices
        prices = [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0,
                  60.0, 55.0, 50.0, 45.0, 40.0, 35.0, 30.0, 25.0]

        result = calc.calculate_rsi(prices, period=14)

        # Strongly declining prices should produce low RSI
        last_rsi = result[-1]
        assert last_rsi < 30, f"Expected RSI < 30 for declining prices, got {last_rsi}"

    def test_rsi_overbought_detection(self):
        """RSI above 70 indicates overbought condition."""
        calc = IndicatorCalculator()
        # Create strongly rising prices
        prices = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,
                  50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]

        result = calc.calculate_rsi(prices, period=14)

        # Strongly rising prices should produce high RSI
        last_rsi = result[-1]
        assert last_rsi > 70, f"Expected RSI > 70 for rising prices, got {last_rsi}"

    def test_rsi_flat_prices(self):
        """RSI should be 50 (neutral) for flat prices."""
        calc = IndicatorCalculator()
        prices = [50.0] * 20

        result = calc.calculate_rsi(prices, period=14)

        # Flat prices might result in undefined RSI (no changes)
        # This is a special case - implementation may return NaN or 50
        import math
        last_rsi = result[-1]
        assert math.isnan(last_rsi) or last_rsi == pytest.approx(50.0, abs=0.1)

    def test_rsi_with_insufficient_data(self):
        """RSI should return NaN for indices before the period is complete."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = calc.calculate_rsi(prices, period=14)

        import math
        for i in range(len(result)):
            assert math.isnan(result[i])


class TestMACD:
    """Tests for MACD calculation."""

    def test_macd_calculation(self):
        """MACD should return macd_line, signal_line, and histogram."""
        calc = IndicatorCalculator()
        # Use enough data for MACD calculation (need at least 26 + 9 = 35 points)
        prices = [float(i) for i in range(50, 100)]

        macd_line, signal_line, histogram = calc.calculate_macd(prices)

        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)

        # Histogram should be macd_line - signal_line
        import math
        for i in range(len(prices)):
            if not math.isnan(macd_line[i]) and not math.isnan(signal_line[i]):
                assert histogram[i] == pytest.approx(macd_line[i] - signal_line[i])

    def test_macd_with_custom_periods(self):
        """MACD should work with custom fast/slow/signal periods."""
        calc = IndicatorCalculator()
        prices = [float(i) for i in range(50, 100)]

        macd_line, signal_line, histogram = calc.calculate_macd(
            prices, fast=8, slow=17, signal=9
        )

        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)

    def test_macd_empty_list(self):
        """MACD should handle empty price list."""
        calc = IndicatorCalculator()

        macd_line, signal_line, histogram = calc.calculate_macd([])

        assert macd_line == []
        assert signal_line == []
        assert histogram == []


class TestBollingerBands:
    """Tests for Bollinger Bands calculation."""

    def test_bollinger_band_calculation(self):
        """Bollinger Bands should calculate upper, middle, and lower correctly."""
        calc = IndicatorCalculator()
        prices = [20.0, 21.0, 22.0, 21.5, 22.5, 23.0, 22.0, 21.0,
                  22.0, 23.0, 24.0, 23.5, 22.5, 21.5, 22.0, 23.0,
                  24.0, 25.0, 24.5, 23.5]

        upper, middle, lower = calc.calculate_bollinger_bands(prices, period=20)

        assert len(upper) == len(prices)
        assert len(middle) == len(prices)
        assert len(lower) == len(prices)

        # At index 19 (first valid point), middle should be SMA
        import math
        for i in range(len(prices)):
            if not math.isnan(upper[i]):
                assert upper[i] > middle[i], "Upper band should be above middle"
                assert lower[i] < middle[i], "Lower band should be below middle"

    def test_bollinger_band_with_custom_std_dev(self):
        """Bollinger Bands should respect custom standard deviation multiplier."""
        calc = IndicatorCalculator()
        prices = [20.0, 21.0, 22.0, 21.5, 22.5, 23.0, 22.0, 21.0,
                  22.0, 23.0, 24.0, 23.5, 22.5, 21.5, 22.0, 23.0,
                  24.0, 25.0, 24.5, 23.5]

        upper1, middle1, lower1 = calc.calculate_bollinger_bands(prices, period=20, std_dev=1.0)
        upper2, middle2, lower2 = calc.calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        # 2 std dev bands should be wider than 1 std dev bands
        import math
        for i in range(len(prices)):
            if not math.isnan(upper1[i]) and not math.isnan(upper2[i]):
                assert upper2[i] > upper1[i], "2 std bands should be wider"
                assert lower2[i] < lower1[i], "2 std bands should be wider"

    def test_bollinger_band_breakout_lower(self):
        """Detect when price breaks below lower band."""
        calc = IndicatorCalculator()
        # Create stable prices then a sharp drop
        prices = [50.0] * 19 + [30.0]  # Sharp drop at the end

        upper, middle, lower = calc.calculate_bollinger_bands(prices, period=20)

        # The last price should be below the lower band
        assert prices[-1] < lower[-1], "Price should break below lower band"

    def test_bollinger_band_breakout_upper(self):
        """Detect when price breaks above upper band."""
        calc = IndicatorCalculator()
        # Create stable prices then a sharp rise
        prices = [50.0] * 19 + [70.0]  # Sharp rise at the end

        upper, middle, lower = calc.calculate_bollinger_bands(prices, period=20)

        # The last price should be above the upper band
        assert prices[-1] > upper[-1], "Price should break above upper band"

    def test_bollinger_band_empty_list(self):
        """Bollinger Bands should handle empty price list."""
        calc = IndicatorCalculator()

        upper, middle, lower = calc.calculate_bollinger_bands([])

        assert upper == []
        assert middle == []
        assert lower == []


class TestVolumeSpike:
    """Tests for volume spike detection."""

    def test_volume_spike_detection(self):
        """Volume spike should be detected when volume exceeds threshold."""
        calc = IndicatorCalculator()
        # Average volume is 100, spike of 250 (2.5x)
        volumes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                   100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                   100.0, 100.0, 100.0, 100.0, 100.0, 250.0]

        result = calc.calculate_volume_spike(volumes, threshold=2.0)

        assert len(result) == len(volumes)
        assert result[-1] is True, "Last volume should be detected as spike"

    def test_volume_no_spike(self):
        """No spike when volume is below threshold."""
        calc = IndicatorCalculator()
        volumes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                   100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                   100.0, 100.0, 100.0, 100.0, 100.0, 150.0]

        result = calc.calculate_volume_spike(volumes, threshold=2.0)

        assert result[-1] is False, "1.5x is below 2.0 threshold"

    def test_volume_spike_custom_threshold(self):
        """Volume spike should work with custom threshold."""
        calc = IndicatorCalculator()
        volumes = [100.0] * 19 + [150.0]

        result = calc.calculate_volume_spike(volumes, threshold=1.5)

        assert result[-1] is True, "1.5x should trigger with 1.5 threshold"

    def test_volume_spike_empty_list(self):
        """Volume spike should handle empty list."""
        calc = IndicatorCalculator()

        result = calc.calculate_volume_spike([])

        assert result == []


class TestGoldenCross:
    """Tests for Golden Cross detection."""

    def test_golden_cross_detection(self):
        """Golden Cross should be detected when short MA crosses above long MA."""
        calc = IndicatorCalculator()
        # Create prices where short MA will cross above long MA at the last index
        # Steady decline, then sharp recovery at the very end
        # Short MA (5) should cross above Long MA (20) at the last price
        prices = [50.0, 48.0, 46.0, 44.0, 42.0, 40.0, 38.0, 36.0, 34.0, 32.0,
                  30.0, 28.0, 26.0, 24.0, 22.0, 20.0, 20.0, 20.0, 20.0, 20.0,
                  22.0, 24.0, 26.0, 35.0, 50.0]  # Sharp spike at end causes cross

        result = calc.detect_golden_cross(prices, short_period=5, long_period=20)

        assert result is True, "Golden cross should be detected"

    def test_golden_cross_not_present(self):
        """Golden Cross should not be detected when not present."""
        calc = IndicatorCalculator()
        # Declining prices - no golden cross
        prices = [50.0, 48.0, 46.0, 44.0, 42.0, 40.0, 38.0, 36.0, 34.0, 32.0,
                  30.0, 28.0, 26.0, 24.0, 22.0, 20.0, 18.0, 16.0, 14.0, 12.0,
                  10.0, 8.0, 6.0, 4.0, 2.0]

        result = calc.detect_golden_cross(prices, short_period=5, long_period=20)

        assert result is False, "No golden cross in declining prices"

    def test_golden_cross_insufficient_data(self):
        """Golden Cross should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.detect_golden_cross(prices, short_period=5, long_period=20)

        assert result is False


class TestDeathCross:
    """Tests for Death Cross detection."""

    def test_death_cross_detection(self):
        """Death Cross should be detected when short MA crosses below long MA."""
        calc = IndicatorCalculator()
        # Create prices where short MA will cross below long MA at the last index
        # Steady rise, then sharp drop at the very end
        # Short MA (5) should cross below Long MA (20) at the last price
        prices = [20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0, 36.0, 38.0,
                  40.0, 42.0, 44.0, 46.0, 48.0, 50.0, 50.0, 50.0, 50.0, 50.0,
                  48.0, 46.0, 44.0, 35.0, 20.0]  # Sharp drop at end causes cross

        result = calc.detect_death_cross(prices, short_period=5, long_period=20)

        assert result is True, "Death cross should be detected"

    def test_death_cross_not_present(self):
        """Death Cross should not be detected when not present."""
        calc = IndicatorCalculator()
        # Rising prices - no death cross
        prices = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0,
                  30.0, 32.0, 34.0, 36.0, 38.0, 40.0, 42.0, 44.0, 46.0, 48.0,
                  50.0, 52.0, 54.0, 56.0, 58.0]

        result = calc.detect_death_cross(prices, short_period=5, long_period=20)

        assert result is False, "No death cross in rising prices"

    def test_death_cross_insufficient_data(self):
        """Death Cross should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.detect_death_cross(prices, short_period=5, long_period=20)

        assert result is False


class TestBNFHelperMethods:
    """Tests for BNF strategy helper methods."""

    def test_is_oversold(self):
        """Test RSI oversold detection helper."""
        calc = IndicatorCalculator()
        # Declining prices for oversold condition
        prices = [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0,
                  60.0, 55.0, 50.0, 45.0, 40.0, 35.0, 30.0, 25.0]

        result = calc.is_oversold(prices, period=14, threshold=30)

        assert result is True

    def test_is_overbought(self):
        """Test RSI overbought detection helper."""
        calc = IndicatorCalculator()
        # Rising prices for overbought condition
        prices = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,
                  50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]

        result = calc.is_overbought(prices, period=14, threshold=70)

        assert result is True

    def test_is_below_lower_band(self):
        """Test if price is below lower Bollinger band."""
        calc = IndicatorCalculator()
        # Stable prices with sharp drop
        prices = [50.0] * 19 + [30.0]

        result = calc.is_below_lower_band(prices, period=20, std_dev=2.0)

        assert result is True

    def test_is_above_upper_band(self):
        """Test if price is above upper Bollinger band."""
        calc = IndicatorCalculator()
        # Stable prices with sharp rise
        prices = [50.0] * 19 + [70.0]

        result = calc.is_above_upper_band(prices, period=20, std_dev=2.0)

        assert result is True


class TestBNFHelperEdgeCases:
    """Tests for BNF helper methods edge cases."""

    def test_is_oversold_insufficient_data(self):
        """is_oversold should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [50.0, 45.0, 40.0]  # Not enough for RSI(14)

        result = calc.is_oversold(prices, period=14, threshold=30)

        assert result is False

    def test_is_overbought_insufficient_data(self):
        """is_overbought should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [50.0, 55.0, 60.0]  # Not enough for RSI(14)

        result = calc.is_overbought(prices, period=14, threshold=70)

        assert result is False

    def test_is_below_lower_band_insufficient_data(self):
        """is_below_lower_band should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [50.0] * 10  # Not enough for period=20

        result = calc.is_below_lower_band(prices, period=20, std_dev=2.0)

        assert result is False

    def test_is_above_upper_band_insufficient_data(self):
        """is_above_upper_band should return False with insufficient data."""
        calc = IndicatorCalculator()
        prices = [50.0] * 10  # Not enough for period=20

        result = calc.is_above_upper_band(prices, period=20, std_dev=2.0)

        assert result is False


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_negative_prices(self):
        """Indicators should handle negative prices (though unusual)."""
        calc = IndicatorCalculator()
        prices = [-10.0, -5.0, 0.0, 5.0, 10.0]

        # Should not raise exception
        result = calc.calculate_sma(prices, period=3)
        assert len(result) == 5

    def test_period_larger_than_data(self):
        """Indicators should handle period larger than data length."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        result = calc.calculate_sma(prices, period=10)

        import math
        assert all(math.isnan(v) for v in result)

    def test_single_price(self):
        """Indicators should handle single price point."""
        calc = IndicatorCalculator()
        prices = [50.0]

        result = calc.calculate_sma(prices, period=1)
        assert result[0] == pytest.approx(50.0)

    def test_zero_period(self):
        """Indicators should handle zero or negative period gracefully."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        with pytest.raises(ValueError):
            calc.calculate_sma(prices, period=0)

    def test_negative_period(self):
        """Indicators should handle negative period gracefully."""
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0]

        with pytest.raises(ValueError):
            calc.calculate_sma(prices, period=-1)

    def test_rsi_single_price(self):
        """RSI with single price should return NaN."""
        calc = IndicatorCalculator()
        prices = [50.0]

        result = calc.calculate_rsi(prices, period=14)

        import math
        assert len(result) == 1
        assert math.isnan(result[0])

    def test_rsi_all_gains_no_loss(self):
        """RSI should be 100 when there are only gains."""
        calc = IndicatorCalculator()
        # All prices going up means RSI should approach 100
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0,
                  18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0]

        result = calc.calculate_rsi(prices, period=14)

        # With only gains, RSI should be 100
        assert result[-1] == pytest.approx(100.0)

    def test_golden_cross_nan_ma_values(self):
        """Golden cross should handle NaN MA values gracefully."""
        calc = IndicatorCalculator()
        # With period 20, we need at least 21 points for valid MAs
        # but 21 points means index 19 and 20 are valid
        prices = [50.0] * 21

        result = calc.detect_golden_cross(prices, short_period=5, long_period=20)

        # With all same prices, no cross should occur
        assert result is False

    def test_death_cross_nan_ma_values(self):
        """Death cross should handle NaN MA values gracefully."""
        calc = IndicatorCalculator()
        prices = [50.0] * 21

        result = calc.detect_death_cross(prices, short_period=5, long_period=20)

        assert result is False
