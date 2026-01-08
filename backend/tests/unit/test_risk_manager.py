"""Unit tests for RiskManager.

Tests for risk management system used in BNF-style swing trading.
Target coverage: 95%+
"""

import pytest

from app.services.risk_manager import (
    RiskAction,
    RiskCheckResult,
    RiskManager,
    TrailingStop,
)


class TestRiskAction:
    """Tests for RiskAction enum."""

    def test_risk_action_values(self):
        """RiskAction should have expected enum values."""
        assert RiskAction.HOLD.value == "hold"
        assert RiskAction.STOP_LOSS.value == "stop_loss"
        assert RiskAction.TAKE_PROFIT.value == "take_profit"
        assert RiskAction.TRAILING_STOP.value == "trailing_stop"


class TestRiskCheckResult:
    """Tests for RiskCheckResult dataclass."""

    def test_risk_check_result_creation(self):
        """RiskCheckResult should store all fields correctly."""
        result = RiskCheckResult(
            action=RiskAction.STOP_LOSS,
            reason="Price dropped below stop-loss threshold",
            current_profit_pct=-5.5,
            trigger_price=9500.0,
        )

        assert result.action == RiskAction.STOP_LOSS
        assert result.reason == "Price dropped below stop-loss threshold"
        assert result.current_profit_pct == -5.5
        assert result.trigger_price == 9500.0

    def test_risk_check_result_default_trigger_price(self):
        """RiskCheckResult should have None as default trigger_price."""
        result = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="No risk action needed",
            current_profit_pct=2.0,
        )

        assert result.trigger_price is None


class TestTrailingStop:
    """Tests for TrailingStop class."""

    def test_trailing_stop_initialization(self):
        """TrailingStop should initialize with correct values."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)

        assert ts.entry_price == 10000.0
        assert ts.trailing_pct == 5.0
        assert ts.highest_price == 10000.0
        assert ts.stop_price == 9500.0  # 10000 * (1 - 5/100)

    def test_trailing_stop_update_price_higher(self):
        """Trailing stop should adjust upward when price rises."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)

        ts.update_price(11000.0)

        assert ts.highest_price == 11000.0
        assert ts.stop_price == 10450.0  # 11000 * (1 - 5/100)

    def test_trailing_stop_update_price_lower(self):
        """Trailing stop should not adjust when price falls."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(11000.0)  # Price goes up first

        ts.update_price(10500.0)  # Price goes down

        assert ts.highest_price == 11000.0  # Should not change
        assert ts.stop_price == 10450.0  # Should not change

    def test_trailing_stop_is_triggered_below_stop(self):
        """Trailing stop should trigger when price falls below stop."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(11000.0)  # highest = 11000, stop = 10450

        result = ts.is_triggered(10400.0)  # Below 10450

        assert result is True

    def test_trailing_stop_is_not_triggered_above_stop(self):
        """Trailing stop should not trigger when price is above stop."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(11000.0)  # highest = 11000, stop = 10450

        result = ts.is_triggered(10500.0)  # Above 10450

        assert result is False

    def test_trailing_stop_is_triggered_at_stop(self):
        """Trailing stop should trigger when price equals stop."""
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(11000.0)  # highest = 11000, stop = 10450

        result = ts.is_triggered(10450.0)  # Exactly at stop

        assert result is True

    def test_trailing_stop_example_from_design_doc(self):
        """Test the example from design document.

        10,000원에 매수, 트레일링 스탑 -5% 설정
        10,000원 → 손절선: 9,500원 (-5%)
        11,000원 → 손절선: 10,450원 (자동 상향!)
        12,000원 → 손절선: 11,400원 (자동 상향!)
        11,400원 도달 → 자동 매도! (수익 +14% 확보)
        """
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)

        # Initial state
        assert ts.stop_price == 9500.0

        # Price rises to 11,000
        ts.update_price(11000.0)
        assert ts.stop_price == 10450.0

        # Price rises to 12,000
        ts.update_price(12000.0)
        assert ts.stop_price == 11400.0

        # Price falls to 11,400 - triggers stop
        assert ts.is_triggered(11400.0) is True


class TestRiskManagerStopLoss:
    """Tests for RiskManager stop-loss functionality."""

    def test_stop_loss_trigger(self):
        """-5% 도달 시 손절 트리거"""
        rm = RiskManager(stop_loss_pct=-5.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=9400.0,  # -6%
        )

        assert result.action == RiskAction.STOP_LOSS
        assert result.current_profit_pct < -5.0
        assert "손절" in result.reason or "stop" in result.reason.lower()

    def test_stop_loss_exactly_at_threshold(self):
        """Stop-loss should trigger exactly at threshold."""
        rm = RiskManager(stop_loss_pct=-5.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=9500.0,  # Exactly -5%
        )

        assert result.action == RiskAction.STOP_LOSS
        assert result.current_profit_pct == pytest.approx(-5.0)

    def test_stop_loss_not_triggered_above_threshold(self):
        """Stop-loss should not trigger above threshold."""
        rm = RiskManager(stop_loss_pct=-5.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=9600.0,  # -4%
        )

        assert result.action == RiskAction.HOLD
        assert result.current_profit_pct == pytest.approx(-4.0)

    def test_stop_loss_custom_percentage(self):
        """Stop-loss should work with custom percentage."""
        rm = RiskManager(stop_loss_pct=-10.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=8900.0,  # -11%
        )

        assert result.action == RiskAction.STOP_LOSS


class TestRiskManagerTakeProfit:
    """Tests for RiskManager take-profit functionality."""

    def test_take_profit_trigger(self):
        """+10% 도달 시 익절 트리거"""
        rm = RiskManager(take_profit_pct=10.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=11100.0,  # +11%
        )

        assert result.action == RiskAction.TAKE_PROFIT
        assert result.current_profit_pct > 10.0
        assert "익절" in result.reason or "profit" in result.reason.lower()

    def test_take_profit_exactly_at_threshold(self):
        """Take-profit should trigger exactly at threshold."""
        rm = RiskManager(take_profit_pct=10.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=11000.0,  # Exactly +10%
        )

        assert result.action == RiskAction.TAKE_PROFIT
        assert result.current_profit_pct == pytest.approx(10.0)

    def test_take_profit_not_triggered_below_threshold(self):
        """Take-profit should not trigger below threshold."""
        rm = RiskManager(take_profit_pct=10.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=10800.0,  # +8%
        )

        assert result.action == RiskAction.HOLD

    def test_take_profit_custom_percentage(self):
        """Take-profit should work with custom percentage."""
        rm = RiskManager(take_profit_pct=20.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=12100.0,  # +21%
        )

        assert result.action == RiskAction.TAKE_PROFIT


class TestRiskManagerTrailingStop:
    """Tests for RiskManager trailing stop functionality."""

    def test_trailing_stop_adjustment(self):
        """가격 상승 시 트레일링 스탑 상향 조정"""
        rm = RiskManager(trailing_stop_enabled=True, trailing_stop_pct=5.0)
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)

        # Simulate price rising
        ts.update_price(12000.0)  # New highest

        assert ts.highest_price == 12000.0
        assert ts.stop_price == 11400.0

    def test_trailing_stop_trigger(self):
        """최고점 대비 하락 시 트레일링 스탑 트리거"""
        # Set take_profit high so trailing stop triggers first
        rm = RiskManager(
            trailing_stop_enabled=True,
            trailing_stop_pct=5.0,
            take_profit_pct=20.0,  # Higher than 13% profit
        )
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(12000.0)  # highest = 12000, stop = 11400

        result = rm.check_position(
            entry_price=10000.0,
            current_price=11300.0,  # Below trailing stop of 11400, +13% profit
            trailing_stop=ts,
        )

        assert result.action == RiskAction.TRAILING_STOP
        assert "트레일링" in result.reason or "trailing" in result.reason.lower()
        assert result.trigger_price == 11400.0

    def test_trailing_stop_not_triggered_when_disabled(self):
        """Trailing stop should not trigger when disabled."""
        rm = RiskManager(trailing_stop_enabled=False, trailing_stop_pct=5.0)
        ts = TrailingStop(entry_price=10000.0, trailing_pct=5.0)
        ts.update_price(12000.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=11300.0,
            trailing_stop=ts,
        )

        # Should use regular take-profit/stop-loss logic
        assert result.action != RiskAction.TRAILING_STOP


class TestRiskManagerHold:
    """Tests for RiskManager HOLD action."""

    def test_hold_within_bounds(self):
        """HOLD should be returned when within stop-loss and take-profit bounds."""
        rm = RiskManager(stop_loss_pct=-5.0, take_profit_pct=10.0)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=10300.0,  # +3%
        )

        assert result.action == RiskAction.HOLD
        assert result.current_profit_pct == pytest.approx(3.0)

    def test_hold_at_entry_price(self):
        """HOLD should be returned at entry price."""
        rm = RiskManager()

        result = rm.check_position(
            entry_price=10000.0,
            current_price=10000.0,
        )

        assert result.action == RiskAction.HOLD
        assert result.current_profit_pct == 0.0


class TestRiskManagerPriority:
    """Tests for risk check priority order."""

    def test_stop_loss_priority_over_trailing_stop(self):
        """Stop-loss should take priority over trailing stop."""
        rm = RiskManager(
            stop_loss_pct=-5.0,
            trailing_stop_enabled=True,
            trailing_stop_pct=3.0,
        )
        ts = TrailingStop(entry_price=10000.0, trailing_pct=3.0)

        # Price dropped significantly, both stop-loss and trailing stop would trigger
        result = rm.check_position(
            entry_price=10000.0,
            current_price=9400.0,  # -6%, triggers stop-loss
            trailing_stop=ts,
        )

        assert result.action == RiskAction.STOP_LOSS


class TestRiskManagerCanOpenPosition:
    """Tests for can_open_position method."""

    def test_max_investment_limit(self):
        """최대 투자금 한도 초과 방지"""
        rm = RiskManager(max_investment_per_stock=1_000_000)

        can_open, reason = rm.can_open_position(
            investment_amount=1_500_000,  # Exceeds limit
            current_positions_count=0,
            daily_pnl_pct=0.0,
        )

        assert can_open is False
        assert "투자금" in reason or "investment" in reason.lower()

    def test_max_stocks_limit(self):
        """최대 보유 종목 수 제한"""
        rm = RiskManager(max_stocks=10)

        can_open, reason = rm.can_open_position(
            investment_amount=500_000,
            current_positions_count=10,  # Already at max
            daily_pnl_pct=0.0,
        )

        assert can_open is False
        assert "종목" in reason or "stock" in reason.lower() or "position" in reason.lower()

    def test_daily_loss_limit(self):
        """일일 손실 한도 초과 시 자동매매 중단"""
        rm = RiskManager(daily_loss_limit=-10.0)

        can_open, reason = rm.can_open_position(
            investment_amount=500_000,
            current_positions_count=0,
            daily_pnl_pct=-12.0,  # Exceeded daily loss limit
        )

        assert can_open is False
        assert "일일" in reason or "daily" in reason.lower()

    def test_can_open_position_success(self):
        """Position can be opened when all conditions are met."""
        rm = RiskManager(
            max_investment_per_stock=1_000_000,
            max_stocks=10,
            daily_loss_limit=-10.0,
        )

        can_open, reason = rm.can_open_position(
            investment_amount=500_000,
            current_positions_count=5,
            daily_pnl_pct=-3.0,
        )

        assert can_open is True
        assert reason == "" or "ok" in reason.lower() or "허용" in reason

    def test_daily_loss_limit_exactly_at_threshold(self):
        """Daily loss limit should trigger exactly at threshold."""
        rm = RiskManager(daily_loss_limit=-10.0)

        can_open, reason = rm.can_open_position(
            investment_amount=500_000,
            current_positions_count=0,
            daily_pnl_pct=-10.0,  # Exactly at limit
        )

        assert can_open is False


class TestRiskManagerPositionSize:
    """Tests for calculate_position_size method."""

    def test_calculate_position_size_basic(self):
        """Position size should be calculated based on risk percentage."""
        rm = RiskManager(
            stop_loss_pct=-5.0,
            max_investment_per_stock=10_000_000,  # High limit so risk calculation applies
        )

        quantity = rm.calculate_position_size(
            available_capital=10_000_000,  # 10M KRW
            stock_price=50_000,
            risk_per_trade_pct=2.0,
        )

        # With 10M capital and 2% risk per trade = 200K risk amount
        # With -5% stop-loss, max investment = 200K / 0.05 = 4M
        # Quantity = 4M / 50K = 80 shares
        assert quantity == 80
        assert quantity > 0

    def test_calculate_position_size_max_investment_limit(self):
        """Position size should respect max investment limit."""
        rm = RiskManager(
            stop_loss_pct=-5.0,
            max_investment_per_stock=1_000_000,
        )

        quantity = rm.calculate_position_size(
            available_capital=10_000_000,
            stock_price=50_000,
            risk_per_trade_pct=2.0,
        )

        # Max investment = 1M, so max quantity = 1M / 50K = 20 shares
        assert quantity <= 20

    def test_calculate_position_size_zero_price(self):
        """Position size should return 0 for zero or negative price."""
        rm = RiskManager()

        quantity = rm.calculate_position_size(
            available_capital=10_000_000,
            stock_price=0,
            risk_per_trade_pct=2.0,
        )

        assert quantity == 0

    def test_calculate_position_size_insufficient_capital(self):
        """Position size should return 0 if capital is insufficient."""
        rm = RiskManager()

        quantity = rm.calculate_position_size(
            available_capital=10_000,  # Too small
            stock_price=50_000,
            risk_per_trade_pct=2.0,
        )

        assert quantity == 0

    def test_calculate_position_size_returns_integer(self):
        """Position size should return integer (whole shares)."""
        rm = RiskManager(stop_loss_pct=-5.0)

        quantity = rm.calculate_position_size(
            available_capital=5_000_000,
            stock_price=33_333,
            risk_per_trade_pct=2.0,
        )

        assert isinstance(quantity, int)


class TestRiskManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_entry_price(self):
        """Check position should handle zero entry price gracefully."""
        rm = RiskManager()

        # Should not raise exception
        result = rm.check_position(
            entry_price=0.0,
            current_price=100.0,
        )

        # When entry price is 0, behavior is undefined but should not crash
        assert result is not None

    def test_negative_prices(self):
        """Check position should handle negative prices gracefully."""
        rm = RiskManager()

        # Should not raise exception
        result = rm.check_position(
            entry_price=100.0,
            current_price=-50.0,
        )

        assert result is not None
        # Negative current price would show significant loss
        assert result.current_profit_pct < 0

    def test_risk_manager_default_initialization(self):
        """RiskManager should initialize with sensible defaults."""
        rm = RiskManager()

        assert rm.stop_loss_pct == -5.0
        assert rm.take_profit_pct == 10.0
        assert rm.trailing_stop_enabled is False
        assert rm.trailing_stop_pct == 5.0
        assert rm.max_investment_per_stock == 1_000_000
        assert rm.max_stocks == 10
        assert rm.daily_loss_limit == -10.0

    def test_trailing_stop_none(self):
        """Check position should work without trailing stop."""
        rm = RiskManager(trailing_stop_enabled=True)

        result = rm.check_position(
            entry_price=10000.0,
            current_price=10500.0,
            trailing_stop=None,
        )

        assert result.action == RiskAction.HOLD


class TestProfitPercentageCalculation:
    """Tests for profit percentage calculation accuracy."""

    def test_profit_calculation_positive(self):
        """Profit percentage should be calculated correctly for gains."""
        rm = RiskManager()

        result = rm.check_position(
            entry_price=10000.0,
            current_price=10500.0,
        )

        assert result.current_profit_pct == pytest.approx(5.0)

    def test_profit_calculation_negative(self):
        """Profit percentage should be calculated correctly for losses."""
        rm = RiskManager()

        result = rm.check_position(
            entry_price=10000.0,
            current_price=9700.0,
        )

        assert result.current_profit_pct == pytest.approx(-3.0)

    def test_profit_calculation_large_gain(self):
        """Profit percentage should be calculated correctly for large gains."""
        rm = RiskManager(take_profit_pct=100.0)  # High threshold to test calculation

        result = rm.check_position(
            entry_price=10000.0,
            current_price=15000.0,
        )

        assert result.current_profit_pct == pytest.approx(50.0)


class TestPositionSizeEdgeCases:
    """Additional edge case tests for calculate_position_size."""

    def test_calculate_position_size_negative_capital(self):
        """Position size should return 0 for negative capital."""
        rm = RiskManager()

        quantity = rm.calculate_position_size(
            available_capital=-1_000_000,
            stock_price=50_000,
            risk_per_trade_pct=2.0,
        )

        assert quantity == 0

    def test_calculate_position_size_zero_stop_loss(self):
        """Position size should use default stop-loss when set to 0."""
        rm = RiskManager(
            stop_loss_pct=0.0,  # Zero stop-loss
            max_investment_per_stock=10_000_000,
        )

        quantity = rm.calculate_position_size(
            available_capital=10_000_000,
            stock_price=50_000,
            risk_per_trade_pct=2.0,
        )

        # Should use default 5% stop-loss
        # risk_amount = 10M * 2% = 200K
        # max_investment = 200K / 0.05 = 4M
        # quantity = 4M / 50K = 80
        assert quantity == 80
