"""Risk Manager for BNF-style swing trading.

This module implements risk management rules for automated trading:
- Stop-loss: Automatic position exit at loss threshold
- Take-profit: Automatic position exit at profit threshold
- Trailing stop: Dynamic stop-loss that follows price upward
- Position sizing: Risk-based calculation of trade size
- Position limits: Maximum investment and stock count limits
- Daily loss limit: Trading halt when daily loss exceeds threshold

Key principles from BNF strategy:
- Strict stop-loss rules
- Emotion-free, mechanical trading
- Capital preservation as priority
"""

from dataclasses import dataclass
from enum import Enum


class RiskAction(Enum):
    """Actions to take based on risk assessment."""

    HOLD = "hold"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class RiskCheckResult:
    """Result of position risk check.

    Attributes:
        action: The risk action to take
        reason: Human-readable explanation of the action
        current_profit_pct: Current profit/loss percentage
        trigger_price: Price that triggered the action (if applicable)
    """

    action: RiskAction
    reason: str
    current_profit_pct: float
    trigger_price: float | None = None


class TrailingStop:
    """Trailing stop tracker.

    Tracks the highest price since entry and calculates a dynamic stop price
    that moves upward as the price rises, locking in profits.

    Example from design doc:
        10,000원에 매수, 트레일링 스탑 -5% 설정
        10,000원 -> 손절선: 9,500원 (-5%)
        11,000원 -> 손절선: 10,450원 (자동 상향!)
        12,000원 -> 손절선: 11,400원 (자동 상향!)
        11,400원 도달 -> 자동 매도! (수익 +14% 확보)
    """

    def __init__(self, entry_price: float, trailing_pct: float):
        """Initialize trailing stop.

        Args:
            entry_price: The price at which the position was entered
            trailing_pct: The trailing percentage (e.g., 5.0 for 5%)
        """
        self.entry_price = entry_price
        self.trailing_pct = trailing_pct
        self.highest_price = entry_price
        self.stop_price = entry_price * (1 - trailing_pct / 100)

    def update_price(self, current_price: float) -> None:
        """Update trailing stop with current price.

        If the current price is higher than the highest recorded price,
        updates the highest price and recalculates the stop price.

        Args:
            current_price: The current market price
        """
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.stop_price = current_price * (1 - self.trailing_pct / 100)

    def is_triggered(self, current_price: float) -> bool:
        """Check if trailing stop is triggered.

        Args:
            current_price: The current market price

        Returns:
            True if current price is at or below the stop price
        """
        return current_price <= self.stop_price


class RiskManager:
    """Risk manager for trading positions.

    Implements risk management rules for BNF-style swing trading:
    - Stop-loss triggers at specified loss percentage
    - Take-profit triggers at specified profit percentage
    - Trailing stop dynamically adjusts with price movement
    - Position limits prevent over-concentration
    - Daily loss limit halts trading

    Risk check priority (from design doc):
    1. Daily loss limit exceeded -> halt trading
    2. Stop-loss line reached -> immediate exit
    3. Take-profit line reached -> immediate exit
    4. Trailing stop triggered -> immediate exit
    5. Otherwise -> HOLD
    """

    def __init__(
        self,
        stop_loss_pct: float = -5.0,
        take_profit_pct: float = 10.0,
        trailing_stop_enabled: bool = False,
        trailing_stop_pct: float = 5.0,
        max_investment_per_stock: float = 1_000_000,
        max_stocks: int = 10,
        daily_loss_limit: float = -10.0,
    ):
        """Initialize risk manager.

        Args:
            stop_loss_pct: Stop-loss threshold as negative percentage (default: -5.0)
            take_profit_pct: Take-profit threshold as positive percentage (default: 10.0)
            trailing_stop_enabled: Whether trailing stop is enabled (default: False)
            trailing_stop_pct: Trailing stop percentage (default: 5.0)
            max_investment_per_stock: Maximum investment per stock in KRW (default: 1,000,000)
            max_stocks: Maximum number of stocks to hold (default: 10)
            daily_loss_limit: Daily loss limit as negative percentage (default: -10.0)
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_pct = trailing_stop_pct
        self.max_investment_per_stock = max_investment_per_stock
        self.max_stocks = max_stocks
        self.daily_loss_limit = daily_loss_limit

    def check_position(
        self,
        entry_price: float,
        current_price: float,
        trailing_stop: TrailingStop | None = None,
    ) -> RiskCheckResult:
        """Check position for risk actions.

        Evaluates the current position against stop-loss, take-profit,
        and trailing stop thresholds.

        Args:
            entry_price: The price at which the position was entered
            current_price: The current market price
            trailing_stop: Optional trailing stop tracker

        Returns:
            RiskCheckResult indicating the action to take
        """
        # Handle edge case of zero entry price
        if entry_price == 0:
            return RiskCheckResult(
                action=RiskAction.HOLD,
                reason="Invalid entry price",
                current_profit_pct=0.0,
            )

        # Calculate profit/loss percentage
        current_profit_pct = ((current_price - entry_price) / entry_price) * 100

        # Priority 1: Stop-loss check
        if current_profit_pct <= self.stop_loss_pct:
            return RiskCheckResult(
                action=RiskAction.STOP_LOSS,
                reason=f"손절 트리거: 현재 손실 {current_profit_pct:.2f}%가 손절선 {self.stop_loss_pct}%에 도달",
                current_profit_pct=current_profit_pct,
                trigger_price=entry_price * (1 + self.stop_loss_pct / 100),
            )

        # Priority 2: Take-profit check
        if current_profit_pct >= self.take_profit_pct:
            return RiskCheckResult(
                action=RiskAction.TAKE_PROFIT,
                reason=f"익절 트리거: 현재 수익 {current_profit_pct:.2f}%가 익절선 {self.take_profit_pct}%에 도달",
                current_profit_pct=current_profit_pct,
                trigger_price=entry_price * (1 + self.take_profit_pct / 100),
            )

        # Priority 3: Trailing stop check (if enabled and provided)
        if self.trailing_stop_enabled and trailing_stop is not None:
            if trailing_stop.is_triggered(current_price):
                return RiskCheckResult(
                    action=RiskAction.TRAILING_STOP,
                    reason=f"트레일링 스탑 트리거: 현재가 {current_price}원이 스탑가 {trailing_stop.stop_price}원 이하",
                    current_profit_pct=current_profit_pct,
                    trigger_price=trailing_stop.stop_price,
                )

        # Default: HOLD
        return RiskCheckResult(
            action=RiskAction.HOLD,
            reason="리스크 조건 미충족 - 포지션 유지",
            current_profit_pct=current_profit_pct,
        )

    def can_open_position(
        self,
        investment_amount: float,
        current_positions_count: int,
        daily_pnl_pct: float,
    ) -> tuple[bool, str]:
        """Check if a new position can be opened.

        Validates against investment limits, position count, and daily loss.

        Args:
            investment_amount: The amount to invest in KRW
            current_positions_count: Current number of open positions
            daily_pnl_pct: Current daily P&L percentage

        Returns:
            Tuple of (can_open, reason) where:
            - can_open: True if position can be opened
            - reason: Empty string if allowed, explanation if not
        """
        # Check daily loss limit first (highest priority)
        if daily_pnl_pct <= self.daily_loss_limit:
            return (
                False,
                f"일일 손실 한도 초과: 현재 일일 손실 {daily_pnl_pct:.2f}%가 한도 {self.daily_loss_limit}%를 초과",
            )

        # Check max investment per stock
        if investment_amount > self.max_investment_per_stock:
            return (
                False,
                f"최대 투자금 한도 초과: {investment_amount:,.0f}원이 한도 {self.max_investment_per_stock:,.0f}원 초과",
            )

        # Check max stocks limit
        if current_positions_count >= self.max_stocks:
            return (
                False,
                f"최대 보유 종목 수 도달: 현재 {current_positions_count}개로 한도 {self.max_stocks}개에 도달",
            )

        return (True, "")

    def calculate_position_size(
        self,
        available_capital: float,
        stock_price: float,
        risk_per_trade_pct: float = 2.0,
    ) -> int:
        """Calculate position size based on risk management.

        Uses the risk amount and stop-loss percentage to determine
        the maximum position size.

        Formula:
            risk_amount = available_capital * (risk_per_trade_pct / 100)
            max_investment = risk_amount / abs(stop_loss_pct / 100)
            quantity = min(max_investment, max_investment_per_stock) / stock_price

        Args:
            available_capital: Available capital for trading in KRW
            stock_price: Price of the stock in KRW
            risk_per_trade_pct: Maximum risk per trade as percentage (default: 2.0)

        Returns:
            Number of shares to buy (integer, rounded down)
        """
        # Handle edge cases
        if stock_price <= 0:
            return 0

        if available_capital <= 0:
            return 0

        # Calculate maximum risk amount for this trade
        risk_amount = available_capital * (risk_per_trade_pct / 100)

        # Calculate maximum investment based on stop-loss
        # If we lose stop_loss_pct%, we lose risk_amount
        stop_loss_ratio = abs(self.stop_loss_pct) / 100
        if stop_loss_ratio == 0:
            stop_loss_ratio = 0.05  # Default to 5% if not set

        max_investment_by_risk = risk_amount / stop_loss_ratio

        # Apply max investment per stock limit
        max_investment = min(max_investment_by_risk, self.max_investment_per_stock)

        # Calculate quantity (whole shares only)
        quantity = int(max_investment / stock_price)

        return quantity
