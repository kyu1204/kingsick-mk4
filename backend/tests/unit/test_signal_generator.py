"""Unit tests for Signal Generator.

Tests the AI-based trading signal generation using BNF strategy.
"""

import math

import pytest

from app.ai.bnf_strategy import BNFStrategy
from app.services.indicator import IndicatorCalculator
from app.services.signal_generator import (
    SignalGenerator,
    SignalType,
    TradingSignal,
)


class TestSignalType:
    """Tests for SignalType enum."""

    def test_signal_type_values(self) -> None:
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"

    def test_signal_type_members(self) -> None:
        """Test that all required signal types exist."""
        assert hasattr(SignalType, "BUY")
        assert hasattr(SignalType, "SELL")
        assert hasattr(SignalType, "HOLD")


class TestTradingSignal:
    """Tests for TradingSignal dataclass."""

    def test_trading_signal_creation(self) -> None:
        """Test creating a TradingSignal instance."""
        signal = TradingSignal(
            signal=SignalType.BUY,
            confidence=0.85,
            reason="RSI oversold with volume spike",
            indicators={"rsi": 25.0, "volume_spike": True},
        )

        assert signal.signal == SignalType.BUY
        assert signal.confidence == 0.85
        assert signal.reason == "RSI oversold with volume spike"
        assert signal.indicators == {"rsi": 25.0, "volume_spike": True}

    def test_trading_signal_equality(self) -> None:
        """Test TradingSignal equality comparison."""
        signal1 = TradingSignal(
            signal=SignalType.BUY,
            confidence=0.8,
            reason="Test",
            indicators={},
        )
        signal2 = TradingSignal(
            signal=SignalType.BUY,
            confidence=0.8,
            reason="Test",
            indicators={},
        )

        assert signal1 == signal2


class TestSignalGenerator:
    """Tests for SignalGenerator class."""

    @pytest.fixture
    def indicator_calculator(self) -> IndicatorCalculator:
        """Create an IndicatorCalculator instance."""
        return IndicatorCalculator()

    @pytest.fixture
    def strategy(self) -> BNFStrategy:
        """Create a BNFStrategy instance."""
        return BNFStrategy()

    @pytest.fixture
    def generator(
        self, indicator_calculator: IndicatorCalculator, strategy: BNFStrategy
    ) -> SignalGenerator:
        """Create a SignalGenerator instance."""
        return SignalGenerator(indicator_calculator, strategy)

    class TestBuySignalGeneration:
        """Tests for buy signal generation."""

        @pytest.fixture
        def generator(self) -> SignalGenerator:
            """Create a SignalGenerator instance."""
            return SignalGenerator(IndicatorCalculator(), BNFStrategy())

        def test_buy_signal_generation(self, generator: SignalGenerator) -> None:
            """Test buy signal is generated for oversold conditions."""
            # Create price data that leads to oversold RSI
            # Steadily declining prices
            prices = [100.0 - i * 2 for i in range(50)]  # 100 -> 2 (steep decline)
            volumes = [1000000.0] * 49 + [3000000.0]  # Volume spike at end

            signal = generator.generate_signal(prices, volumes)

            assert signal.signal == SignalType.BUY
            assert signal.confidence > 0.5
            assert "rsi" in signal.indicators

        def test_buy_signal_includes_reason(self, generator: SignalGenerator) -> None:
            """Test buy signal includes descriptive reason."""
            prices = [100.0 - i * 2 for i in range(50)]
            volumes = [1000000.0] * 49 + [3000000.0]

            signal = generator.generate_signal(prices, volumes)

            if signal.signal == SignalType.BUY:
                assert len(signal.reason) > 0
                # Reason should mention key factors
                reason_lower = signal.reason.lower()
                assert any(
                    term in reason_lower
                    for term in ["rsi", "oversold", "volume", "bollinger"]
                )

    class TestSellSignalGeneration:
        """Tests for sell signal generation."""

        @pytest.fixture
        def generator(self) -> SignalGenerator:
            """Create a SignalGenerator instance."""
            return SignalGenerator(IndicatorCalculator(), BNFStrategy())

        def test_sell_signal_generation(self, generator: SignalGenerator) -> None:
            """Test sell signal is generated for overbought conditions."""
            # Create price data that leads to overbought RSI
            # Steadily rising prices
            prices = [50.0 + i * 2 for i in range(50)]  # 50 -> 148 (steep rise)
            volumes = [1000000.0] * 50  # Normal volume (no spike = decrease relative)

            signal = generator.generate_signal(prices, volumes)

            assert signal.signal == SignalType.SELL
            assert signal.confidence > 0.5
            assert "rsi" in signal.indicators

        def test_sell_signal_includes_reason(self, generator: SignalGenerator) -> None:
            """Test sell signal includes descriptive reason."""
            prices = [50.0 + i * 2 for i in range(50)]
            volumes = [1000000.0] * 50

            signal = generator.generate_signal(prices, volumes)

            if signal.signal == SignalType.SELL:
                assert len(signal.reason) > 0
                reason_lower = signal.reason.lower()
                assert any(
                    term in reason_lower
                    for term in ["rsi", "overbought", "volume", "bollinger"]
                )

    class TestHoldSignalGeneration:
        """Tests for hold signal generation."""

        @pytest.fixture
        def generator(self) -> SignalGenerator:
            """Create a SignalGenerator instance."""
            return SignalGenerator(IndicatorCalculator(), BNFStrategy())

        def test_hold_signal_generation(self, generator: SignalGenerator) -> None:
            """Test hold signal is generated for neutral conditions."""
            # Create price data with neutral indicators
            # Oscillating prices around a mean
            import math

            prices = [100.0 + 5 * math.sin(i / 5) for i in range(50)]
            volumes = [1000000.0] * 50

            signal = generator.generate_signal(prices, volumes)

            # In neutral conditions, should be HOLD
            assert signal.signal == SignalType.HOLD
            assert signal.confidence >= 0.0

        def test_hold_signal_with_insufficient_data(
            self, generator: SignalGenerator
        ) -> None:
            """Test hold signal when data is insufficient."""
            prices = [100.0, 101.0, 99.0]  # Too few data points
            volumes = [1000000.0] * 3

            signal = generator.generate_signal(prices, volumes)

            # With insufficient data, should return HOLD
            assert signal.signal == SignalType.HOLD

    class TestConfidenceCalculation:
        """Tests for signal confidence calculation."""

        @pytest.fixture
        def generator(self) -> SignalGenerator:
            """Create a SignalGenerator instance."""
            return SignalGenerator(IndicatorCalculator(), BNFStrategy())

        def test_confidence_calculation_all_conditions_met(
            self, generator: SignalGenerator
        ) -> None:
            """Test confidence when all buy conditions are met."""
            buy_conditions = [True, True, True]  # RSI, volume, Bollinger
            sell_conditions = [False, False, False]

            confidence = generator.calculate_confidence(buy_conditions, sell_conditions)

            assert confidence >= 0.9  # High confidence for all conditions

        def test_confidence_calculation_partial_conditions(
            self, generator: SignalGenerator
        ) -> None:
            """Test confidence when some conditions are met."""
            buy_conditions = [True, True, False]  # 2 of 3
            sell_conditions = [False, False, False]

            confidence = generator.calculate_confidence(buy_conditions, sell_conditions)

            assert 0.5 <= confidence <= 0.8  # Moderate confidence

        def test_confidence_calculation_no_conditions(
            self, generator: SignalGenerator
        ) -> None:
            """Test confidence when no conditions are met."""
            buy_conditions = [False, False, False]
            sell_conditions = [False, False, False]

            confidence = generator.calculate_confidence(buy_conditions, sell_conditions)

            assert confidence < 0.5  # Low confidence

        def test_confidence_bounds(self, generator: SignalGenerator) -> None:
            """Test that confidence is always within 0.0 to 1.0."""
            test_cases = [
                ([True, True, True], [False, False, False]),
                ([False, False, False], [True, True, True]),
                ([True, False, True], [False, True, False]),
                ([], []),
            ]

            for buy_conds, sell_conds in test_cases:
                confidence = generator.calculate_confidence(buy_conds, sell_conds)
                assert 0.0 <= confidence <= 1.0


class TestSignalGeneratorIndicators:
    """Tests for indicator values in generated signals."""

    @pytest.fixture
    def generator(self) -> SignalGenerator:
        """Create a SignalGenerator instance."""
        return SignalGenerator(IndicatorCalculator(), BNFStrategy())

    def test_signal_contains_rsi(self, generator: SignalGenerator) -> None:
        """Test that generated signal contains RSI indicator."""
        prices = [100.0 + i for i in range(50)]
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        assert "rsi" in signal.indicators
        rsi = signal.indicators["rsi"]
        assert not math.isnan(rsi)
        assert 0.0 <= rsi <= 100.0

    def test_signal_contains_macd(self, generator: SignalGenerator) -> None:
        """Test that generated signal contains MACD indicator."""
        prices = [100.0 + i for i in range(50)]
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        assert "macd_histogram" in signal.indicators

    def test_signal_contains_bollinger_info(self, generator: SignalGenerator) -> None:
        """Test that generated signal contains Bollinger band info."""
        prices = [100.0 + i for i in range(50)]
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        # Should have Bollinger band position indicators
        assert "below_lower_band" in signal.indicators or "above_upper_band" in signal.indicators

    def test_signal_contains_volume_spike(self, generator: SignalGenerator) -> None:
        """Test that generated signal contains volume spike indicator."""
        prices = [100.0 + i for i in range(50)]
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        assert "volume_spike" in signal.indicators


class TestSignalGeneratorEdgeCases:
    """Edge case tests for SignalGenerator."""

    @pytest.fixture
    def generator(self) -> SignalGenerator:
        """Create a SignalGenerator instance."""
        return SignalGenerator(IndicatorCalculator(), BNFStrategy())

    def test_empty_price_data(self, generator: SignalGenerator) -> None:
        """Test handling of empty price data."""
        prices: list[float] = []
        volumes: list[float] = []

        signal = generator.generate_signal(prices, volumes)

        assert signal.signal == SignalType.HOLD
        assert signal.confidence == 0.0

    def test_single_price_point(self, generator: SignalGenerator) -> None:
        """Test handling of single price point."""
        prices = [100.0]
        volumes = [1000000.0]

        signal = generator.generate_signal(prices, volumes)

        assert signal.signal == SignalType.HOLD

    def test_mismatched_price_volume_length(self, generator: SignalGenerator) -> None:
        """Test handling when price and volume lengths differ."""
        prices = [100.0 + i for i in range(50)]
        volumes = [1000000.0] * 30  # Shorter than prices

        # Should handle gracefully
        try:
            signal = generator.generate_signal(prices, volumes)
            assert signal is not None
        except ValueError:
            pass  # Also acceptable to raise ValueError

    def test_all_same_prices(self, generator: SignalGenerator) -> None:
        """Test with constant price (no movement)."""
        prices = [100.0] * 50
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        # With no price movement, should be HOLD
        assert signal.signal == SignalType.HOLD

    def test_very_volatile_prices(self, generator: SignalGenerator) -> None:
        """Test with highly volatile price data."""
        # Alternating high and low
        prices = [100.0 if i % 2 == 0 else 50.0 for i in range(50)]
        volumes = [1000000.0] * 50

        signal = generator.generate_signal(prices, volumes)

        # Should not crash and return valid signal
        assert signal.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0.0 <= signal.confidence <= 1.0


class TestSignalGeneratorIntegration:
    """Integration tests for SignalGenerator with real calculations."""

    @pytest.fixture
    def generator(self) -> SignalGenerator:
        """Create a SignalGenerator instance."""
        return SignalGenerator(IndicatorCalculator(), BNFStrategy())

    def test_realistic_bullish_scenario(self, generator: SignalGenerator) -> None:
        """Test with realistic bullish market data after a dip."""
        # Sharp decline followed by stabilization at bottom
        prices = (
            [100.0 - i * 2 for i in range(30)]  # Decline
            + [40.0 - i * 0.5 for i in range(10)]  # Further decline
            + [35.0 + i * 0.1 for i in range(10)]  # Stabilization
        )
        volumes = (
            [1000000.0] * 40
            + [2500000.0] * 10  # Volume spike at bottom
        )

        signal = generator.generate_signal(prices, volumes)

        # In oversold conditions with volume spike, expect BUY
        assert signal.signal in [SignalType.BUY, SignalType.HOLD]

    def test_realistic_bearish_scenario(self, generator: SignalGenerator) -> None:
        """Test with realistic bearish market data after a rally."""
        # Sharp rise followed by exhaustion at top
        prices = (
            [50.0 + i * 2 for i in range(30)]  # Rise
            + [110.0 + i * 1 for i in range(10)]  # Continued rise
            + [120.0 - i * 0.1 for i in range(10)]  # Exhaustion
        )
        volumes = (
            [2000000.0] * 30
            + [1500000.0] * 10  # Volume decreasing
            + [1000000.0] * 10  # Low volume at top
        )

        signal = generator.generate_signal(prices, volumes)

        # In overbought conditions with decreasing volume, expect SELL
        assert signal.signal in [SignalType.SELL, SignalType.HOLD]

    def test_signal_reason_generation(self, generator: SignalGenerator) -> None:
        """Test that reason text is meaningful and descriptive."""
        prices = [100.0 - i * 2 for i in range(50)]
        volumes = [1000000.0] * 49 + [3000000.0]

        signal = generator.generate_signal(prices, volumes)

        # Reason should not be empty
        assert signal.reason
        assert len(signal.reason) >= 10  # At least a short description

    def test_multiple_signals_consistency(self, generator: SignalGenerator) -> None:
        """Test that same data produces consistent signals."""
        prices = [100.0 - i * 2 for i in range(50)]
        volumes = [1000000.0] * 49 + [3000000.0]

        signal1 = generator.generate_signal(prices, volumes)
        signal2 = generator.generate_signal(prices, volumes)

        assert signal1.signal == signal2.signal
        assert signal1.confidence == signal2.confidence
