"""Trading engine with dual-mode support (AUTO/ALERT).

This module implements the core trading engine that orchestrates
the BNF-style swing trading strategy with two operational modes:
- AUTO: Automatic order execution
- ALERT: Notification only, requiring manual approval

The engine integrates:
- KIS API client for market data and order execution
- Signal generator for AI-based trading signals
- Risk manager for position risk assessment
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.services.kis_api import (
    KISApiClient,
    KISApiError,
    OrderResult,
    OrderSide,
    Position,
    StockPrice,
)
from app.services.risk_manager import (
    RiskAction,
    RiskCheckResult,
    RiskManager,
    TrailingStop,
)
from app.services.signal_generator import SignalGenerator, SignalType, TradingSignal

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading engine operational mode.

    AUTO: Automatic order execution without manual intervention
    ALERT: Notification only, orders require manual approval
    """

    AUTO = "auto"
    ALERT = "alert"


@dataclass
class TradingLoopResult:
    """Result of a trading loop execution.

    Attributes:
        processed_stocks: Number of stocks processed
        signals_generated: Number of trading signals generated
        orders_executed: Number of orders executed (AUTO mode)
        alerts_sent: Number of alerts sent (ALERT mode or notifications)
        errors: List of error messages encountered
    """

    processed_stocks: int
    signals_generated: int
    orders_executed: int
    alerts_sent: int
    errors: list[str] = field(default_factory=list)


@dataclass
class AlertInfo:
    """Pending alert information for ALERT mode.

    Stores the signal details for pending approval/rejection.

    Attributes:
        alert_id: Unique identifier for the alert
        stock_code: Stock code for the alert
        signal: Trading signal that triggered the alert
        signal_type: Type of signal (BUY/SELL)
        current_price: Price at the time of alert
        suggested_quantity: Suggested order quantity
        position: Position for sell alerts
        created_at: Alert creation timestamp
    """

    alert_id: str
    stock_code: str
    signal: TradingSignal
    signal_type: SignalType
    current_price: float
    suggested_quantity: int
    position: Position | None = None
    created_at: datetime = field(default_factory=datetime.now)


class TradingEngine:
    """Dual-mode automated trading engine.

    Implements the core trading logic for BNF-style swing trading:
    1. Fetches market data for watchlist and positions
    2. Calculates technical indicators
    3. Generates AI trading signals
    4. Checks position risk (stop-loss, take-profit, trailing stop)
    5. Executes orders (AUTO) or sends alerts (ALERT)

    Args:
        mode: Operating mode (AUTO or ALERT)
        kis_client: KIS API client for market data and orders
        signal_generator: AI signal generator
        risk_manager: Risk management service
    """

    def __init__(
        self,
        mode: TradingMode,
        kis_client: KISApiClient,
        signal_generator: SignalGenerator,
        risk_manager: RiskManager,
    ) -> None:
        """Initialize the trading engine.

        Args:
            mode: Operating mode (AUTO or ALERT)
            kis_client: KIS API client instance
            signal_generator: Signal generator instance
            risk_manager: Risk manager instance
        """
        self.mode = mode
        self._kis_client = kis_client
        self._signal_generator = signal_generator
        self._risk_manager = risk_manager
        self._trailing_stops: dict[str, TrailingStop] = {}
        self._pending_alerts: dict[str, AlertInfo] = {}
        self._daily_pnl_pct: float = 0.0

    def set_mode(self, mode: TradingMode) -> None:
        """Change the trading mode.

        Args:
            mode: New trading mode (AUTO or ALERT)
        """
        logger.info(f"Trading mode changed from {self.mode.value} to {mode.value}")
        self.mode = mode

    def get_trailing_stops(self) -> dict[str, TrailingStop]:
        """Get all active trailing stops.

        Returns:
            Dictionary mapping stock codes to TrailingStop instances
        """
        return self._trailing_stops.copy()

    def get_pending_alerts(self) -> list[AlertInfo]:
        """Get all pending alerts awaiting approval.

        Returns:
            List of AlertInfo for pending alerts
        """
        return list(self._pending_alerts.values())

    def update_trailing_stop(self, stock_code: str, current_price: float) -> None:
        """Update trailing stop for a stock with new price.

        Args:
            stock_code: Stock code to update
            current_price: Current market price
        """
        if stock_code in self._trailing_stops:
            self._trailing_stops[stock_code].update_price(current_price)

    async def run_trading_loop(
        self,
        watchlist: list[str],
        positions: list[Position],
    ) -> TradingLoopResult:
        """Execute the main trading loop.

        Process flow:
        1. Fetch current prices for watchlist and positions
        2. For each position: check risk conditions
        3. For each stock: generate trading signals
        4. Execute orders (AUTO) or send alerts (ALERT)

        Args:
            watchlist: List of stock codes to monitor
            positions: List of current positions

        Returns:
            TradingLoopResult with execution statistics
        """
        result = TradingLoopResult(
            processed_stocks=0,
            signals_generated=0,
            orders_executed=0,
            alerts_sent=0,
            errors=[],
        )

        # Handle empty inputs
        if not watchlist and not positions:
            return result

        # Collect all stock codes to fetch
        position_codes = [p.stock_code for p in positions]
        all_codes = list(set(watchlist + position_codes))

        try:
            # Fetch current prices
            stock_prices = await self._kis_client.get_stock_prices(all_codes)
            price_map: dict[str, StockPrice] = {sp.code: sp for sp in stock_prices}
            result.processed_stocks = len(stock_prices)
        except KISApiError as e:
            error_msg = f"Failed to fetch stock prices: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return result

        # Process positions for risk check
        for position in positions:
            try:
                await self._process_position(
                    position=position,
                    price_map=price_map,
                    result=result,
                )
            except Exception as e:
                error_msg = f"Error processing position {position.stock_code}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Process watchlist for buy signals
        for stock_code in watchlist:
            # Skip if already in position (avoid duplicate processing)
            if stock_code in position_codes:
                continue

            try:
                await self._process_watchlist_stock(
                    stock_code=stock_code,
                    price_map=price_map,
                    positions_count=len(positions),
                    result=result,
                )
            except Exception as e:
                error_msg = f"Error processing watchlist {stock_code}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        return result

    async def _process_position(
        self,
        position: Position,
        price_map: dict[str, StockPrice],
        result: TradingLoopResult,
    ) -> None:
        """Process a position for risk check and sell signals.

        Args:
            position: Position to process
            price_map: Map of stock codes to current prices
            result: TradingLoopResult to update
        """
        stock_code = position.stock_code

        # Ensure trailing stop exists for position
        if stock_code not in self._trailing_stops:
            self._trailing_stops[stock_code] = TrailingStop(
                entry_price=position.avg_price,
                trailing_pct=self._risk_manager.trailing_stop_pct,
            )

        # Get current price
        stock_price = price_map.get(stock_code)
        if not stock_price:
            return

        current_price = stock_price.current_price

        # Update trailing stop with current price
        self.update_trailing_stop(stock_code, current_price)

        # Check position risk
        risk_result = await self.check_position_risk(
            position=position,
            trailing_stops=self._trailing_stops,
        )

        # Handle risk-triggered sells
        if risk_result.action in (
            RiskAction.STOP_LOSS,
            RiskAction.TAKE_PROFIT,
            RiskAction.TRAILING_STOP,
        ):
            # Create synthetic sell signal from risk check
            sell_signal = TradingSignal(
                signal=SignalType.SELL,
                confidence=1.0,  # Risk-triggered = high confidence
                reason=risk_result.reason,
                indicators={"risk_action": risk_result.action.value},
            )

            order_result = await self._execute_sell(
                signal=sell_signal,
                position=position,
                result=result,
            )

            if order_result and order_result.success:
                # Remove trailing stop for closed position
                self._trailing_stops.pop(stock_code, None)

            return

        # Get daily prices for signal generation
        try:
            daily_prices = await self._kis_client.get_daily_prices(stock_code)
            prices = [d["close"] for d in daily_prices]
            volumes = [float(d["volume"]) for d in daily_prices]

            # Generate trading signal
            signal = self._signal_generator.generate_signal(prices, volumes)
            result.signals_generated += 1

            # Process sell signal
            if signal.signal == SignalType.SELL:
                await self._execute_sell(
                    signal=signal,
                    position=position,
                    result=result,
                )

        except Exception as e:
            logger.warning(f"Failed to generate signal for {stock_code}: {e}")

    async def _process_watchlist_stock(
        self,
        stock_code: str,
        price_map: dict[str, StockPrice],
        positions_count: int,
        result: TradingLoopResult,
    ) -> None:
        """Process a watchlist stock for buy signals.

        Args:
            stock_code: Stock code to process
            price_map: Map of stock codes to current prices
            positions_count: Current number of positions
            result: TradingLoopResult to update
        """
        stock_price = price_map.get(stock_code)
        if not stock_price:
            return

        current_price = stock_price.current_price

        # Get daily prices for signal generation
        try:
            daily_prices = await self._kis_client.get_daily_prices(stock_code)
            prices = [d["close"] for d in daily_prices]
            volumes = [float(d["volume"]) for d in daily_prices]

            # Generate trading signal
            signal = self._signal_generator.generate_signal(prices, volumes)
            result.signals_generated += 1

            # Process buy signal
            if signal.signal == SignalType.BUY:
                await self._execute_buy(
                    signal=signal,
                    stock_code=stock_code,
                    current_price=current_price,
                    positions_count=positions_count,
                    result=result,
                )

        except Exception as e:
            logger.warning(f"Failed to generate signal for {stock_code}: {e}")

    async def _execute_buy(
        self,
        signal: TradingSignal,
        stock_code: str,
        current_price: float,
        positions_count: int,
        result: TradingLoopResult,
    ) -> OrderResult | None:
        """Execute or alert for a buy signal.

        Args:
            signal: Buy signal
            stock_code: Stock code to buy
            current_price: Current stock price
            positions_count: Number of current positions
            result: TradingLoopResult to update

        Returns:
            OrderResult if order executed, None otherwise
        """
        # Get available capital
        try:
            balance = await self._kis_client.get_balance()
            available_amount = balance.get("available_amount", 0)
        except KISApiError:
            available_amount = 0

        # Calculate position size
        quantity = self._risk_manager.calculate_position_size(
            available_capital=available_amount,
            stock_price=current_price,
        )

        if quantity <= 0:
            return None

        # Calculate investment amount
        investment_amount = current_price * quantity

        # Check if position can be opened
        can_open, reason = self._risk_manager.can_open_position(
            investment_amount=investment_amount,
            current_positions_count=positions_count,
            daily_pnl_pct=self._daily_pnl_pct,
        )

        if not can_open:
            logger.info(f"Cannot open position for {stock_code}: {reason}")
            return None

        # Execute based on mode
        if self.mode == TradingMode.AUTO:
            order_result = await self._kis_client.place_order(
                stock_code=stock_code,
                side=OrderSide.BUY,
                quantity=quantity,
                price=None,  # Market order
            )

            if order_result.success:
                result.orders_executed += 1
                logger.info(
                    f"Buy order executed: {stock_code}, qty={quantity}, "
                    f"order_id={order_result.order_id}"
                )
            else:
                logger.warning(f"Buy order failed: {order_result.message}")

            return order_result

        else:  # ALERT mode
            alert = AlertInfo(
                alert_id=str(uuid.uuid4()),
                stock_code=stock_code,
                signal=signal,
                signal_type=SignalType.BUY,
                current_price=current_price,
                suggested_quantity=quantity,
            )
            self._pending_alerts[alert.alert_id] = alert
            result.alerts_sent += 1
            logger.info(f"Buy alert created: {stock_code}, alert_id={alert.alert_id}")
            return None

    async def _execute_sell(
        self,
        signal: TradingSignal,
        position: Position,
        result: TradingLoopResult,
    ) -> OrderResult | None:
        """Execute or alert for a sell signal.

        Args:
            signal: Sell signal
            position: Position to sell
            result: TradingLoopResult to update

        Returns:
            OrderResult if order executed, None otherwise
        """
        stock_code = position.stock_code
        quantity = position.quantity

        if self.mode == TradingMode.AUTO:
            order_result = await self._kis_client.place_order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=quantity,
                price=None,  # Market order
            )

            if order_result.success:
                result.orders_executed += 1
                logger.info(
                    f"Sell order executed: {stock_code}, qty={quantity}, "
                    f"order_id={order_result.order_id}, reason={signal.reason}"
                )
            else:
                logger.warning(f"Sell order failed: {order_result.message}")

            return order_result

        else:  # ALERT mode
            alert = AlertInfo(
                alert_id=str(uuid.uuid4()),
                stock_code=stock_code,
                signal=signal,
                signal_type=SignalType.SELL,
                current_price=position.current_price,
                suggested_quantity=quantity,
                position=position,
            )
            self._pending_alerts[alert.alert_id] = alert
            result.alerts_sent += 1
            logger.info(f"Sell alert created: {stock_code}, alert_id={alert.alert_id}")
            return None

    async def process_buy_signal(
        self,
        signal: TradingSignal,
        stock_code: str,
        current_price: float,
    ) -> OrderResult | None:
        """Process a buy signal directly.

        This method is for direct signal processing outside the trading loop.

        Args:
            signal: Buy trading signal
            stock_code: Stock code to buy
            current_price: Current stock price

        Returns:
            OrderResult if executed (AUTO mode), None otherwise (ALERT mode)
        """
        result = TradingLoopResult(0, 0, 0, 0, [])
        return await self._execute_buy(
            signal=signal,
            stock_code=stock_code,
            current_price=current_price,
            positions_count=0,  # Assume no position limit check needed
            result=result,
        )

    async def process_sell_signal(
        self,
        signal: TradingSignal,
        position: Position,
    ) -> OrderResult | None:
        """Process a sell signal directly.

        This method is for direct signal processing outside the trading loop.

        Args:
            signal: Sell trading signal
            position: Position to sell

        Returns:
            OrderResult if executed (AUTO mode), None otherwise (ALERT mode)
        """
        result = TradingLoopResult(0, 0, 0, 0, [])
        return await self._execute_sell(
            signal=signal,
            position=position,
            result=result,
        )

    async def check_position_risk(
        self,
        position: Position,
        trailing_stops: dict[str, TrailingStop],
    ) -> RiskCheckResult:
        """Check position for risk triggers.

        Evaluates stop-loss, take-profit, and trailing stop conditions.

        Args:
            position: Position to check
            trailing_stops: Dictionary of trailing stops by stock code

        Returns:
            RiskCheckResult with action and reason
        """
        trailing_stop = trailing_stops.get(position.stock_code)

        return self._risk_manager.check_position(
            entry_price=position.avg_price,
            current_price=position.current_price,
            trailing_stop=trailing_stop,
        )

    async def approve_alert(self, alert_id: str) -> OrderResult | None:
        """Approve a pending alert and execute the order.

        Args:
            alert_id: ID of the alert to approve

        Returns:
            OrderResult if order executed successfully, None if alert not found
        """
        alert = self._pending_alerts.pop(alert_id, None)
        if not alert:
            logger.warning(f"Alert not found: {alert_id}")
            return None

        if alert.signal_type == SignalType.BUY:
            order_result = await self._kis_client.place_order(
                stock_code=alert.stock_code,
                side=OrderSide.BUY,
                quantity=alert.suggested_quantity,
                price=None,  # Market order
            )
        else:  # SELL
            order_result = await self._kis_client.place_order(
                stock_code=alert.stock_code,
                side=OrderSide.SELL,
                quantity=alert.suggested_quantity,
                price=None,  # Market order
            )

        if order_result.success:
            logger.info(
                f"Alert approved and order executed: {alert.stock_code}, "
                f"order_id={order_result.order_id}"
            )
        else:
            logger.warning(f"Alert approved but order failed: {order_result.message}")

        return order_result

    def reject_alert(self, alert_id: str) -> bool:
        """Reject a pending alert without executing.

        Args:
            alert_id: ID of the alert to reject

        Returns:
            True if alert was found and rejected, False otherwise
        """
        alert = self._pending_alerts.pop(alert_id, None)
        if alert:
            logger.info(f"Alert rejected: {alert.stock_code}, alert_id={alert_id}")
            return True
        logger.warning(f"Alert not found for rejection: {alert_id}")
        return False

    def set_daily_pnl(self, pnl_pct: float) -> None:
        """Set the daily P&L percentage for risk checks.

        Args:
            pnl_pct: Daily profit/loss percentage
        """
        self._daily_pnl_pct = pnl_pct

    def clear_trailing_stops(self) -> None:
        """Clear all trailing stops."""
        self._trailing_stops.clear()

    def clear_pending_alerts(self) -> None:
        """Clear all pending alerts."""
        self._pending_alerts.clear()
