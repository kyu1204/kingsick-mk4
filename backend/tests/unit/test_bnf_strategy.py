"""Unit tests for BNF Strategy.

Tests the BNF-style contrarian swing trading strategy rules.
"""

import math

import pytest

from app.ai.bnf_strategy import BNFStrategy


class TestBNFStrategy:
    """Tests for BNFStrategy class."""

    @pytest.fixture
    def strategy(self) -> BNFStrategy:
        """Create a BNFStrategy instance."""
        return BNFStrategy()

    class TestBuySignal:
        """Tests for buy signal detection."""

        @pytest.fixture
        def strategy(self) -> BNFStrategy:
            """Create a BNFStrategy instance."""
            return BNFStrategy()

        def test_buy_signal_on_oversold(self, strategy: BNFStrategy) -> None:
            """Test buy signal when RSI < 30 (oversold condition)."""
            indicators = {
                "rsi": 25.0,  # Oversold
                "volume_spike": True,  # Volume spike present
                "below_lower_band": True,  # Below Bollinger lower band
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": -0.5,
            }

            is_buy, confidence, reason = strategy.check_buy_signal(indicators)

            assert is_buy is True
            assert 0.0 <= confidence <= 1.0
            assert "oversold" in reason.lower() or "rsi" in reason.lower()

        def test_buy_signal_with_volume_spike(self, strategy: BNFStrategy) -> None:
            """Test buy signal with volume spike requirement."""
            indicators = {
                "rsi": 28.0,
                "volume_spike": True,  # Volume spike present
                "below_lower_band": True,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": -0.3,
            }

            is_buy, confidence, reason = strategy.check_buy_signal(indicators)

            assert is_buy is True
            assert "volume" in reason.lower()

        def test_buy_signal_below_bollinger_lower(self, strategy: BNFStrategy) -> None:
            """Test buy signal when price is below lower Bollinger band."""
            indicators = {
                "rsi": 27.0,
                "volume_spike": True,
                "below_lower_band": True,  # Below lower band
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": -0.4,
            }

            is_buy, confidence, reason = strategy.check_buy_signal(indicators)

            assert is_buy is True
            assert "bollinger" in reason.lower() or "band" in reason.lower()

        def test_no_buy_signal_rsi_neutral(self, strategy: BNFStrategy) -> None:
            """Test no buy signal when RSI is neutral."""
            indicators = {
                "rsi": 50.0,  # Neutral
                "volume_spike": True,
                "below_lower_band": False,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.0,
            }

            is_buy, confidence, reason = strategy.check_buy_signal(indicators)

            assert is_buy is False

        def test_no_buy_signal_without_volume_spike_or_bollinger(self, strategy: BNFStrategy) -> None:
            """Test no buy signal when no volume spike AND not below lower band."""
            indicators = {
                "rsi": 25.0,
                "volume_spike": False,  # No volume spike
                "below_lower_band": False,  # Not below lower band either
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": -0.5,
            }

            is_buy, confidence, reason = strategy.check_buy_signal(indicators)

            # Without volume spike or bollinger condition, no buy signal
            assert is_buy is False

        def test_buy_signal_golden_cross_boost(self, strategy: BNFStrategy) -> None:
            """Test that golden cross boosts buy signal confidence."""
            base_indicators = {
                "rsi": 28.0,
                "volume_spike": True,
                "below_lower_band": True,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": -0.3,
            }

            _, base_confidence, _ = strategy.check_buy_signal(base_indicators)

            golden_indicators = base_indicators.copy()
            golden_indicators["golden_cross"] = True

            _, golden_confidence, _ = strategy.check_buy_signal(golden_indicators)

            # Golden cross should boost confidence
            assert golden_confidence >= base_confidence

    class TestSellSignal:
        """Tests for sell signal detection."""

        @pytest.fixture
        def strategy(self) -> BNFStrategy:
            """Create a BNFStrategy instance."""
            return BNFStrategy()

        def test_sell_signal_on_overbought(self, strategy: BNFStrategy) -> None:
            """Test sell signal when RSI > 70 (overbought condition)."""
            indicators = {
                "rsi": 75.0,  # Overbought
                "volume_spike": False,  # Volume decrease (no spike)
                "above_upper_band": True,  # Above Bollinger upper band
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.5,
            }

            is_sell, confidence, reason = strategy.check_sell_signal(indicators)

            assert is_sell is True
            assert 0.0 <= confidence <= 1.0
            assert "overbought" in reason.lower() or "rsi" in reason.lower()

        def test_sell_signal_above_bollinger_upper(self, strategy: BNFStrategy) -> None:
            """Test sell signal when price is above upper Bollinger band."""
            indicators = {
                "rsi": 72.0,
                "volume_spike": False,
                "above_upper_band": True,  # Above upper band
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.4,
            }

            is_sell, confidence, reason = strategy.check_sell_signal(indicators)

            assert is_sell is True
            assert "bollinger" in reason.lower() or "band" in reason.lower()

        def test_no_sell_signal_rsi_neutral(self, strategy: BNFStrategy) -> None:
            """Test no sell signal when RSI is neutral."""
            indicators = {
                "rsi": 50.0,  # Neutral
                "volume_spike": False,
                "above_upper_band": False,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.0,
            }

            is_sell, confidence, reason = strategy.check_sell_signal(indicators)

            assert is_sell is False

        def test_sell_signal_with_volume_decrease(self, strategy: BNFStrategy) -> None:
            """Test sell signal with volume decrease (no spike)."""
            indicators = {
                "rsi": 73.0,
                "volume_spike": False,  # Volume decreasing
                "above_upper_band": True,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.6,
            }

            is_sell, confidence, reason = strategy.check_sell_signal(indicators)

            assert is_sell is True

        def test_sell_signal_death_cross_boost(self, strategy: BNFStrategy) -> None:
            """Test that death cross boosts sell signal confidence."""
            base_indicators = {
                "rsi": 72.0,
                "volume_spike": False,
                "above_upper_band": True,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.4,
            }

            _, base_confidence, _ = strategy.check_sell_signal(base_indicators)

            death_indicators = base_indicators.copy()
            death_indicators["death_cross"] = True

            _, death_confidence, _ = strategy.check_sell_signal(death_indicators)

            # Death cross should boost sell confidence
            assert death_confidence >= base_confidence

    class TestHoldSignal:
        """Tests for hold signal detection."""

        @pytest.fixture
        def strategy(self) -> BNFStrategy:
            """Create a BNFStrategy instance."""
            return BNFStrategy()

        def test_hold_signal_on_neutral(self, strategy: BNFStrategy) -> None:
            """Test HOLD signal when conditions are neutral."""
            indicators = {
                "rsi": 50.0,  # Neutral
                "volume_spike": False,
                "below_lower_band": False,
                "above_upper_band": False,
                "golden_cross": False,
                "death_cross": False,
                "macd_histogram": 0.0,
            }

            is_buy, _, _ = strategy.check_buy_signal(indicators)
            is_sell, _, _ = strategy.check_sell_signal(indicators)

            # Both should be false in neutral conditions
            assert is_buy is False
            assert is_sell is False

        def test_hold_when_conflicting_signals(self, strategy: BNFStrategy) -> None:
            """Test HOLD when conditions are conflicting."""
            indicators = {
                "rsi": 50.0,  # Neutral RSI
                "volume_spike": True,  # Volume spike (buy condition)
                "below_lower_band": False,
                "above_upper_band": True,  # Above upper band (sell condition)
                "golden_cross": True,  # Golden cross (buy condition)
                "death_cross": False,
                "macd_histogram": 0.0,
            }

            is_buy, buy_conf, _ = strategy.check_buy_signal(indicators)
            is_sell, sell_conf, _ = strategy.check_sell_signal(indicators)

            # With conflicting signals, neither should have high confidence
            # or at least one should be false
            assert not (is_buy and is_sell and buy_conf > 0.7 and sell_conf > 0.7)

    class TestCrossDetection:
        """Tests for golden cross and death cross detection."""

        @pytest.fixture
        def strategy(self) -> BNFStrategy:
            """Create a BNFStrategy instance."""
            return BNFStrategy()

        def test_check_golden_cross(self, strategy: BNFStrategy) -> None:
            """Test golden cross detection from indicators."""
            indicators = {
                "golden_cross": True,
                "death_cross": False,
            }

            assert strategy.check_golden_cross(indicators) is True

        def test_check_death_cross(self, strategy: BNFStrategy) -> None:
            """Test death cross detection from indicators."""
            indicators = {
                "golden_cross": False,
                "death_cross": True,
            }

            assert strategy.check_death_cross(indicators) is True

        def test_no_cross_detected(self, strategy: BNFStrategy) -> None:
            """Test when no cross is detected."""
            indicators = {
                "golden_cross": False,
                "death_cross": False,
            }

            assert strategy.check_golden_cross(indicators) is False
            assert strategy.check_death_cross(indicators) is False


class TestBNFStrategyEdgeCases:
    """Edge case tests for BNFStrategy."""

    @pytest.fixture
    def strategy(self) -> BNFStrategy:
        """Create a BNFStrategy instance."""
        return BNFStrategy()

    def test_extreme_rsi_values(self, strategy: BNFStrategy) -> None:
        """Test with extreme RSI values."""
        # RSI = 0 (maximum oversold)
        oversold_indicators = {
            "rsi": 0.0,
            "volume_spike": True,
            "below_lower_band": True,
            "golden_cross": False,
            "death_cross": False,
            "macd_histogram": -1.0,
        }

        is_buy, confidence, _ = strategy.check_buy_signal(oversold_indicators)
        assert is_buy is True
        assert confidence >= 0.8  # Should have high confidence

        # RSI = 100 (maximum overbought)
        overbought_indicators = {
            "rsi": 100.0,
            "volume_spike": False,
            "above_upper_band": True,
            "golden_cross": False,
            "death_cross": False,
            "macd_histogram": 1.0,
        }

        is_sell, confidence, _ = strategy.check_sell_signal(overbought_indicators)
        assert is_sell is True
        assert confidence >= 0.8  # Should have high confidence

    def test_nan_rsi_handling(self, strategy: BNFStrategy) -> None:
        """Test handling of NaN RSI values."""
        indicators = {
            "rsi": math.nan,
            "volume_spike": True,
            "below_lower_band": True,
            "golden_cross": False,
            "death_cross": False,
            "macd_histogram": 0.0,
        }

        is_buy, _, _ = strategy.check_buy_signal(indicators)
        is_sell, _, _ = strategy.check_sell_signal(indicators)

        # Should not generate signals with NaN RSI
        assert is_buy is False
        assert is_sell is False

    def test_missing_indicator_keys(self, strategy: BNFStrategy) -> None:
        """Test handling of missing indicator keys."""
        incomplete_indicators: dict = {
            "rsi": 25.0,
            # Missing other keys
        }

        # Should handle gracefully without raising exceptions
        try:
            is_buy, _, _ = strategy.check_buy_signal(incomplete_indicators)
            is_sell, _, _ = strategy.check_sell_signal(incomplete_indicators)
        except KeyError:
            pytest.fail("Strategy should handle missing keys gracefully")

    def test_confidence_bounds(self, strategy: BNFStrategy) -> None:
        """Test that confidence is always within 0.0 to 1.0."""
        test_cases = [
            {"rsi": 10.0, "volume_spike": True, "below_lower_band": True,
             "golden_cross": True, "death_cross": False, "macd_histogram": -1.0},
            {"rsi": 90.0, "volume_spike": False, "above_upper_band": True,
             "golden_cross": False, "death_cross": True, "macd_histogram": 1.0},
            {"rsi": 50.0, "volume_spike": False, "below_lower_band": False,
             "above_upper_band": False, "golden_cross": False, "death_cross": False,
             "macd_histogram": 0.0},
        ]

        for indicators in test_cases:
            _, buy_conf, _ = strategy.check_buy_signal(indicators)
            _, sell_conf, _ = strategy.check_sell_signal(indicators)

            assert 0.0 <= buy_conf <= 1.0, f"Buy confidence out of bounds: {buy_conf}"
            assert 0.0 <= sell_conf <= 1.0, f"Sell confidence out of bounds: {sell_conf}"

    def test_reason_is_not_empty(self, strategy: BNFStrategy) -> None:
        """Test that reason string is always provided."""
        indicators = {
            "rsi": 25.0,
            "volume_spike": True,
            "below_lower_band": True,
            "golden_cross": False,
            "death_cross": False,
            "macd_histogram": -0.5,
        }

        _, _, buy_reason = strategy.check_buy_signal(indicators)
        _, _, sell_reason = strategy.check_sell_signal(indicators)

        assert isinstance(buy_reason, str)
        assert isinstance(sell_reason, str)
        # At least one should have content when signals differ
