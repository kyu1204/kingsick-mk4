"""Backtesting engine for BNF-style swing trading strategy.

This module provides the BacktestEngine class that simulates trading
on historical data to evaluate strategy performance.
"""

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from app.ai.bnf_strategy import BNFStrategy
from app.services.indicator import IndicatorCalculator
from app.services.signal_generator import SignalGenerator, SignalType


@dataclass
class BacktestConfig:
    """Backtest configuration parameters.

    Attributes:
        initial_capital: Starting capital in KRW
        commission_rate: Trading commission rate (0.00015 = 0.015%)
        tax_rate: Securities transaction tax rate (0.0023 = 0.23%)
        slippage: Assumed slippage rate (0.001 = 0.1%)
        stop_loss_pct: Stop loss percentage (5.0 = 5%)
        take_profit_pct: Take profit percentage (10.0 = 10%)
        max_position_pct: Maximum position size as % of capital (20.0 = 20%)
        max_positions: Maximum number of concurrent positions
    """

    initial_capital: float = 10_000_000
    commission_rate: float = 0.00015
    tax_rate: float = 0.0023
    slippage: float = 0.001
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    max_position_pct: float = 20.0
    max_positions: int = 5


@dataclass
class BacktestTrade:
    """Record of a simulated trade.

    Attributes:
        trade_date: Date of the trade
        stock_code: Stock ticker symbol
        side: Trade direction (BUY or SELL)
        price: Execution price
        quantity: Number of shares
        amount: Total transaction amount
        commission: Commission paid
        tax: Tax paid (only on sell)
        signal_reason: Reason for the trade signal
        pnl: Profit/loss for this trade (only for closing trades)
        pnl_pct: Profit/loss percentage (only for closing trades)
    """

    trade_date: date
    stock_code: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    amount: float
    commission: float
    tax: float
    signal_reason: str
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class Position:
    """Active trading position.

    Attributes:
        stock_code: Stock ticker symbol
        entry_date: Date position was opened
        entry_price: Entry price per share
        quantity: Number of shares held
        current_price: Current market price
    """

    stock_code: str
    entry_date: date
    entry_price: float
    quantity: int
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized profit/loss percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100


@dataclass
class BacktestResult:
    """Complete backtest results.

    Attributes:
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting capital
        final_capital: Ending capital
        total_return_pct: Total return percentage
        cagr: Compound annual growth rate
        mdd: Maximum drawdown percentage
        sharpe_ratio: Sharpe ratio (risk-adjusted return)
        win_rate: Percentage of winning trades
        profit_factor: Gross profit / Gross loss
        total_trades: Total number of trades
        winning_trades: Number of profitable trades
        losing_trades: Number of losing trades
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount
        max_win: Largest winning trade
        max_loss: Largest losing trade
        trades: List of all executed trades
        daily_equity: Daily equity values
        daily_returns: Daily return percentages
        drawdown_curve: Daily drawdown percentages
    """

    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr: float
    mdd: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    max_win: float
    max_loss: float
    trades: list[BacktestTrade] = field(default_factory=list)
    daily_equity: list[float] = field(default_factory=list)
    daily_returns: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)


class BacktestEngine:
    """Backtesting engine for trading strategy simulation.

    This engine simulates the BNF trading strategy on historical data,
    accounting for transaction costs and risk management rules.
    """

    # Annualization factor for daily returns (trading days per year)
    TRADING_DAYS_PER_YEAR = 252

    # Risk-free rate for Sharpe ratio (Korean 1-year treasury ~3.5%)
    RISK_FREE_RATE = 0.035

    def __init__(
        self,
        config: BacktestConfig | None = None,
        indicator_calculator: IndicatorCalculator | None = None,
        signal_generator: SignalGenerator | None = None,
    ) -> None:
        """Initialize the backtest engine.

        Args:
            config: Backtest configuration. Uses defaults if None.
            indicator_calculator: IndicatorCalculator instance. Creates new if None.
            signal_generator: SignalGenerator instance. Creates new if None.
        """
        self.config = config or BacktestConfig()

        if indicator_calculator is None:
            indicator_calculator = IndicatorCalculator()
        self.indicator = indicator_calculator

        if signal_generator is None:
            strategy = BNFStrategy()
            signal_generator = SignalGenerator(indicator_calculator, strategy)
        self.signal_generator = signal_generator

        self._cash: float = 0.0
        self._positions: dict[str, Position] = {}
        self._trades: list[BacktestTrade] = []
        self._equity_curve: list[float] = []
        self._dates: list[date] = []

    def run(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        """Run backtest simulation.

        Args:
            price_data: Dictionary mapping stock_code to list of OHLCV dicts.
                       Each dict has keys: date, open, high, low, close, volume
            start_date: Simulation start date
            end_date: Simulation end date

        Returns:
            BacktestResult with all performance metrics
        """
        self._reset()
        self._cash = self.config.initial_capital

        all_dates = self._extract_trading_days(price_data, start_date, end_date)

        if not all_dates:
            return self._create_empty_result(start_date, end_date)

        for current_date in all_dates:
            self._dates.append(current_date)
            self._update_position_prices(price_data, current_date)
            self._check_exits(price_data, current_date)
            self._check_entries(price_data, current_date)
            self._record_equity()

        return self._calculate_results(start_date, end_date)

    def _reset(self) -> None:
        """Reset internal state for new simulation."""
        self._cash = 0.0
        self._positions = {}
        self._trades = []
        self._equity_curve = []
        self._dates = []

    def _extract_trading_days(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        start_date: date,
        end_date: date,
    ) -> list[date]:
        """Extract sorted list of trading days from price data."""
        all_dates: set[date] = set()

        for stock_code, prices in price_data.items():
            for price_point in prices:
                d = price_point.get("date")
                if isinstance(d, date) and start_date <= d <= end_date:
                    all_dates.add(d)

        return sorted(all_dates)

    def _update_position_prices(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        current_date: date,
    ) -> None:
        """Update current prices for all positions."""
        for stock_code, position in self._positions.items():
            prices = price_data.get(stock_code, [])
            for price_point in prices:
                if price_point.get("date") == current_date:
                    position.current_price = price_point.get("close", position.entry_price)
                    break

    def _check_exits(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        current_date: date,
    ) -> None:
        """Check exit conditions for existing positions."""
        positions_to_close: list[tuple[str, str]] = []

        for stock_code, position in self._positions.items():
            pnl_pct = position.unrealized_pnl_pct

            if pnl_pct <= -self.config.stop_loss_pct:
                positions_to_close.append((stock_code, f"Stop loss triggered ({pnl_pct:.1f}%)"))
                continue

            if pnl_pct >= self.config.take_profit_pct:
                positions_to_close.append((stock_code, f"Take profit triggered ({pnl_pct:.1f}%)"))
                continue

            prices = self._get_price_history(price_data, stock_code, current_date)
            volumes = self._get_volume_history(price_data, stock_code, current_date)

            if len(prices) >= SignalGenerator.MIN_DATA_POINTS:
                signal = self.signal_generator.generate_signal(prices, volumes)
                if signal.signal == SignalType.SELL:
                    positions_to_close.append((stock_code, signal.reason))

        for stock_code, reason in positions_to_close:
            self._execute_sell(stock_code, current_date, reason)

    def _check_entries(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        current_date: date,
    ) -> None:
        """Check entry signals for new positions."""
        if len(self._positions) >= self.config.max_positions:
            return

        for stock_code in price_data.keys():
            if stock_code in self._positions:
                continue

            if len(self._positions) >= self.config.max_positions:
                break

            prices = self._get_price_history(price_data, stock_code, current_date)
            volumes = self._get_volume_history(price_data, stock_code, current_date)

            if len(prices) < SignalGenerator.MIN_DATA_POINTS:
                continue

            signal = self.signal_generator.generate_signal(prices, volumes)

            if signal.signal == SignalType.BUY and signal.confidence >= 0.5:
                current_price = prices[-1]
                self._execute_buy(stock_code, current_date, current_price, signal.reason)

    def _get_price_history(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        stock_code: str,
        current_date: date,
    ) -> list[float]:
        """Get price history up to and including current date."""
        prices = price_data.get(stock_code, [])
        return [
            p.get("close", 0.0)
            for p in prices
            if p.get("date") is not None and p.get("date") <= current_date
        ]

    def _get_volume_history(
        self,
        price_data: dict[str, list[dict[str, Any]]],
        stock_code: str,
        current_date: date,
    ) -> list[float]:
        """Get volume history up to and including current date."""
        prices = price_data.get(stock_code, [])
        return [
            float(p.get("volume", 0))
            for p in prices
            if p.get("date") is not None and p.get("date") <= current_date
        ]

    def _execute_buy(
        self,
        stock_code: str,
        trade_date: date,
        price: float,
        reason: str,
    ) -> None:
        """Execute a buy order."""
        execution_price = price * (1 + self.config.slippage)

        max_position_value = self._total_equity() * (self.config.max_position_pct / 100)
        available_cash = min(self._cash, max_position_value)

        available_for_shares = available_cash / (1 + self.config.commission_rate)
        quantity = int(available_for_shares / execution_price)

        if quantity <= 0:
            return

        amount = execution_price * quantity
        commission = amount * self.config.commission_rate
        total_cost = amount + commission

        if total_cost > self._cash:
            return

        self._cash -= total_cost
        self._positions[stock_code] = Position(
            stock_code=stock_code,
            entry_date=trade_date,
            entry_price=execution_price,
            quantity=quantity,
            current_price=execution_price,
        )

        self._trades.append(
            BacktestTrade(
                trade_date=trade_date,
                stock_code=stock_code,
                side="BUY",
                price=execution_price,
                quantity=quantity,
                amount=amount,
                commission=commission,
                tax=0.0,
                signal_reason=reason,
            )
        )

    def _execute_sell(
        self,
        stock_code: str,
        trade_date: date,
        reason: str,
    ) -> None:
        """Execute a sell order."""
        position = self._positions.get(stock_code)
        if position is None:
            return

        execution_price = position.current_price * (1 - self.config.slippage)

        amount = execution_price * position.quantity
        commission = amount * self.config.commission_rate
        tax = amount * self.config.tax_rate

        entry_amount = position.entry_price * position.quantity
        pnl = amount - entry_amount - commission - tax

        proceeds = amount - commission - tax
        self._cash += proceeds

        self._trades.append(
            BacktestTrade(
                trade_date=trade_date,
                stock_code=stock_code,
                side="SELL",
                price=execution_price,
                quantity=position.quantity,
                amount=amount,
                commission=commission,
                tax=tax,
                signal_reason=reason,
                pnl=pnl,
                pnl_pct=((execution_price / position.entry_price) - 1) * 100,
            )
        )

        del self._positions[stock_code]

    def _total_equity(self) -> float:
        """Calculate total portfolio equity (cash + positions)."""
        position_value = sum(p.current_price * p.quantity for p in self._positions.values())
        return self._cash + position_value

    def _record_equity(self) -> None:
        """Record current equity value."""
        self._equity_curve.append(self._total_equity())

    def _calculate_results(
        self,
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        """Calculate all performance metrics."""
        if not self._equity_curve:
            return self._create_empty_result(start_date, end_date)

        final_capital = self._equity_curve[-1]
        total_return_pct = ((final_capital / self.config.initial_capital) - 1) * 100

        days = (end_date - start_date).days
        years = days / 365.25 if days > 0 else 1
        cagr = self._calculate_cagr(self.config.initial_capital, final_capital, years)

        daily_returns = self._calculate_daily_returns()
        mdd = self._calculate_mdd()
        drawdown_curve = self._calculate_drawdown_curve()
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

        sell_trades = [t for t in self._trades if t.side == "SELL"]
        winning_trades = [t for t in sell_trades if t.pnl > 0]
        losing_trades = [t for t in sell_trades if t.pnl <= 0]

        win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0.0

        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        avg_win = (
            (sum(t.pnl for t in winning_trades) / len(winning_trades)) if winning_trades else 0.0
        )
        avg_loss = (
            (sum(t.pnl for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        )

        max_win = max((t.pnl for t in winning_trades), default=0.0)
        max_loss = min((t.pnl for t in losing_trades), default=0.0)

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return_pct,
            cagr=cagr,
            mdd=mdd,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor if profit_factor != float("inf") else 999.99,
            total_trades=len(self._trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_win=max_win,
            max_loss=max_loss,
            trades=self._trades,
            daily_equity=self._equity_curve,
            daily_returns=daily_returns,
            drawdown_curve=drawdown_curve,
        )

    def _calculate_cagr(
        self,
        initial: float,
        final: float,
        years: float,
    ) -> float:
        """Calculate Compound Annual Growth Rate."""
        if initial <= 0 or years <= 0:
            return 0.0
        if final <= 0:
            return -100.0

        return (pow(final / initial, 1 / years) - 1) * 100

    def _calculate_daily_returns(self) -> list[float]:
        """Calculate daily return percentages."""
        if len(self._equity_curve) < 2:
            return []

        returns: list[float] = []
        for i in range(1, len(self._equity_curve)):
            prev = self._equity_curve[i - 1]
            curr = self._equity_curve[i]
            if prev > 0:
                returns.append(((curr / prev) - 1) * 100)
            else:
                returns.append(0.0)

        return returns

    def _calculate_mdd(self) -> float:
        """Calculate Maximum Drawdown percentage."""
        if not self._equity_curve:
            return 0.0

        peak = self._equity_curve[0]
        max_drawdown = 0.0

        for equity in self._equity_curve:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _calculate_drawdown_curve(self) -> list[float]:
        """Calculate drawdown curve."""
        if not self._equity_curve:
            return []

        peak = self._equity_curve[0]
        drawdowns: list[float] = []

        for equity in self._equity_curve:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
            drawdowns.append(drawdown)

        return drawdowns

    def _calculate_sharpe_ratio(self, daily_returns: list[float]) -> float:
        """Calculate Sharpe Ratio: (Annualized Return - Risk Free Rate) / Annualized Volatility."""
        if len(daily_returns) < 2:
            return 0.0

        returns = [r / 100 for r in daily_returns]
        mean_return = sum(returns) / len(returns)

        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev == 0:
            return 0.0

        annualized_return = mean_return * self.TRADING_DAYS_PER_YEAR
        annualized_std = std_dev * math.sqrt(self.TRADING_DAYS_PER_YEAR)

        return (annualized_return - self.RISK_FREE_RATE) / annualized_std

    def _create_empty_result(
        self,
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        """Create empty result when no data available."""
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_return_pct=0.0,
            cagr=0.0,
            mdd=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0.0,
            avg_loss=0.0,
            max_win=0.0,
            max_loss=0.0,
        )
