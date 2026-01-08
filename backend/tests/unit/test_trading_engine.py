"""Unit tests for TradingEngine.

This module contains comprehensive tests for the dual-mode trading engine
that implements AUTO and ALERT trading modes for BNF-style swing trading.

Target coverage: 90%+
"""

from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
import pytest

from app.services.trading_engine import (
    TradingMode,
    TradingLoopResult,
    AlertInfo,
    TradingEngine,
)
from app.services.kis_api import (
    KISApiClient,
    OrderResult,
    OrderStatus,
    OrderSide,
    Position,
    StockPrice,
)
from app.services.signal_generator import SignalGenerator, SignalType, TradingSignal
from app.services.risk_manager import (
    RiskManager,
    RiskCheckResult,
    RiskAction,
    TrailingStop,
)


@pytest.fixture
def mock_kis_client() -> AsyncMock:
    """Create mock KIS API client."""
    client = AsyncMock(spec=KISApiClient)
    return client


@pytest.fixture
def mock_signal_generator() -> MagicMock:
    """Create mock signal generator."""
    generator = MagicMock(spec=SignalGenerator)
    return generator


@pytest.fixture
def mock_risk_manager() -> MagicMock:
    """Create mock risk manager."""
    manager = MagicMock(spec=RiskManager)
    manager.stop_loss_pct = -5.0
    manager.take_profit_pct = 10.0
    manager.trailing_stop_enabled = True
    manager.trailing_stop_pct = 5.0
    manager.max_investment_per_stock = 1_000_000
    return manager


@pytest.fixture
def sample_stock_price() -> StockPrice:
    """Create sample stock price data."""
    return StockPrice(
        code="005930",
        name="Samsung Electronics",
        current_price=70000,
        change_rate=1.5,
        volume=10000000,
        high=71000,
        low=69000,
        open=69500,
    )


@pytest.fixture
def sample_position() -> Position:
    """Create sample position data."""
    return Position(
        stock_code="005930",
        stock_name="Samsung Electronics",
        quantity=10,
        avg_price=65000,
        current_price=70000,
        profit_loss=50000,
        profit_loss_rate=7.69,
    )


@pytest.fixture
def sample_buy_signal() -> TradingSignal:
    """Create sample buy signal."""
    return TradingSignal(
        signal=SignalType.BUY,
        confidence=0.85,
        reason="RSI oversold, below lower Bollinger band",
        indicators={"rsi": 28.5, "current_price": 70000},
    )


@pytest.fixture
def sample_sell_signal() -> TradingSignal:
    """Create sample sell signal."""
    return TradingSignal(
        signal=SignalType.SELL,
        confidence=0.80,
        reason="RSI overbought, above upper Bollinger band",
        indicators={"rsi": 72.5, "current_price": 70000},
    )


@pytest.fixture
def sample_hold_signal() -> TradingSignal:
    """Create sample hold signal."""
    return TradingSignal(
        signal=SignalType.HOLD,
        confidence=0.50,
        reason="No clear trading signal",
        indicators={"rsi": 50.0, "current_price": 70000},
    )


@pytest.fixture
def sample_daily_prices() -> list[dict]:
    """Create sample daily OHLCV data."""
    prices = []
    base_price = 70000
    for i in range(50):
        prices.append({
            "date": f"2024010{i:02d}",
            "open": base_price + i * 100,
            "high": base_price + i * 100 + 500,
            "low": base_price + i * 100 - 300,
            "close": base_price + i * 100 + 200,
            "volume": 1000000 + i * 10000,
        })
    return prices


class TestTradingMode:
    """Test TradingMode enum."""

    def test_auto_mode_value(self):
        """AUTO mode should have value 'auto'."""
        assert TradingMode.AUTO.value == "auto"

    def test_alert_mode_value(self):
        """ALERT mode should have value 'alert'."""
        assert TradingMode.ALERT.value == "alert"


class TestTradingLoopResult:
    """Test TradingLoopResult dataclass."""

    def test_result_creation(self):
        """TradingLoopResult should store all fields correctly."""
        result = TradingLoopResult(
            processed_stocks=5,
            signals_generated=3,
            orders_executed=2,
            alerts_sent=1,
            errors=["Error 1"],
        )
        assert result.processed_stocks == 5
        assert result.signals_generated == 3
        assert result.orders_executed == 2
        assert result.alerts_sent == 1
        assert result.errors == ["Error 1"]


class TestTradingEngineInit:
    """Test TradingEngine initialization."""

    def test_init_auto_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Should initialize in AUTO mode."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )
        assert engine.mode == TradingMode.AUTO

    def test_init_alert_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Should initialize in ALERT mode."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )
        assert engine.mode == TradingMode.ALERT


class TestModeSwitching:
    """Test trading mode switching."""

    def test_switch_auto_to_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Should switch from AUTO to ALERT mode."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )
        engine.set_mode(TradingMode.ALERT)
        assert engine.mode == TradingMode.ALERT

    def test_switch_alert_to_auto(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Should switch from ALERT to AUTO mode."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )
        engine.set_mode(TradingMode.AUTO)
        assert engine.mode == TradingMode.AUTO


class TestAutoModeBuySignal:
    """Test AUTO mode buy signal processing."""

    @pytest.mark.asyncio
    async def test_auto_mode_buy_signal_executes_order(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """AUTO mode: buy signal should automatically execute order."""
        # Arrange
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD001",
            message="Order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Assert
        assert result.orders_executed >= 1
        mock_kis_client.place_order.assert_called()

    @pytest.mark.asyncio
    async def test_auto_mode_buy_blocked_by_risk(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """AUTO mode: buy signal blocked by risk manager should not execute."""
        # Arrange
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (False, "Daily loss limit exceeded")

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Assert
        mock_kis_client.place_order.assert_not_called()


class TestAutoModeSellSignal:
    """Test AUTO mode sell signal processing."""

    @pytest.mark.asyncio
    async def test_auto_mode_sell_signal_executes_order(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_sell_signal: TradingSignal,
        sample_position: Position,
        sample_daily_prices: list[dict],
    ):
        """AUTO mode: sell signal should automatically execute order."""
        # Arrange
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD002",
            message="Order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_sell_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="No risk trigger",
            current_profit_pct=7.69,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        # Assert
        assert result.orders_executed >= 1
        mock_kis_client.place_order.assert_called()


class TestAlertModeBuySignal:
    """Test ALERT mode buy signal processing."""

    @pytest.mark.asyncio
    async def test_alert_mode_buy_signal_sends_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """ALERT mode: buy signal should send alert instead of order."""
        # Arrange
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Assert
        assert result.alerts_sent >= 1
        mock_kis_client.place_order.assert_not_called()


class TestAlertModeSellSignal:
    """Test ALERT mode sell signal processing."""

    @pytest.mark.asyncio
    async def test_alert_mode_sell_signal_sends_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_sell_signal: TradingSignal,
        sample_position: Position,
        sample_daily_prices: list[dict],
    ):
        """ALERT mode: sell signal should send alert instead of order."""
        # Arrange
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_signal_generator.generate_signal.return_value = sample_sell_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="No risk trigger",
            current_profit_pct=7.69,
        )

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        # Assert
        assert result.alerts_sent >= 1
        mock_kis_client.place_order.assert_not_called()


class TestRiskCheckStopLoss:
    """Test risk check stop-loss trigger."""

    @pytest.mark.asyncio
    async def test_stop_loss_trigger_executes_sell(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_hold_signal: TradingSignal,
        sample_position: Position,
        sample_daily_prices: list[dict],
    ):
        """Stop-loss trigger should execute sell in AUTO mode."""
        # Arrange - modify price to trigger stop-loss
        stop_loss_price = StockPrice(
            code="005930",
            name="Samsung Electronics",
            current_price=60000,  # Below stop-loss
            change_rate=-7.69,
            volume=10000000,
            high=61000,
            low=59000,
            open=62000,
        )
        stop_loss_position = Position(
            stock_code="005930",
            stock_name="Samsung Electronics",
            quantity=10,
            avg_price=65000,
            current_price=60000,
            profit_loss=-50000,
            profit_loss_rate=-7.69,
        )
        mock_kis_client.get_stock_prices.return_value = [stop_loss_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD003",
            message="Stop-loss order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_hold_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.STOP_LOSS,
            reason="Stop-loss triggered at -7.69%",
            current_profit_pct=-7.69,
            trigger_price=61750.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[stop_loss_position],
        )

        # Assert
        assert result.orders_executed >= 1
        mock_kis_client.place_order.assert_called()


class TestRiskCheckTakeProfit:
    """Test risk check take-profit trigger."""

    @pytest.mark.asyncio
    async def test_take_profit_trigger_executes_sell(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_hold_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Take-profit trigger should execute sell in AUTO mode."""
        # Arrange
        take_profit_price = StockPrice(
            code="005930",
            name="Samsung Electronics",
            current_price=75000,  # Above take-profit
            change_rate=15.38,
            volume=10000000,
            high=76000,
            low=74000,
            open=74500,
        )
        take_profit_position = Position(
            stock_code="005930",
            stock_name="Samsung Electronics",
            quantity=10,
            avg_price=65000,
            current_price=75000,
            profit_loss=100000,
            profit_loss_rate=15.38,
        )
        mock_kis_client.get_stock_prices.return_value = [take_profit_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD004",
            message="Take-profit order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_hold_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.TAKE_PROFIT,
            reason="Take-profit triggered at +15.38%",
            current_profit_pct=15.38,
            trigger_price=71500.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[take_profit_position],
        )

        # Assert
        assert result.orders_executed >= 1


class TestRiskCheckTrailingStop:
    """Test risk check trailing stop trigger."""

    @pytest.mark.asyncio
    async def test_trailing_stop_trigger_executes_sell(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_hold_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Trailing stop trigger should execute sell in AUTO mode."""
        # Arrange
        trailing_stop_price = StockPrice(
            code="005930",
            name="Samsung Electronics",
            current_price=71400,  # Dropped to trailing stop level
            change_rate=9.85,
            volume=10000000,
            high=72000,
            low=71000,
            open=72500,
        )
        trailing_position = Position(
            stock_code="005930",
            stock_name="Samsung Electronics",
            quantity=10,
            avg_price=65000,
            current_price=71400,
            profit_loss=64000,
            profit_loss_rate=9.85,
        )
        mock_kis_client.get_stock_prices.return_value = [trailing_stop_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD005",
            message="Trailing stop order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_hold_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.TRAILING_STOP,
            reason="Trailing stop triggered",
            current_profit_pct=9.85,
            trigger_price=71400.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[trailing_position],
        )

        # Assert
        assert result.orders_executed >= 1


class TestTradingLoopFullCycle:
    """Test full trading loop cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_with_watchlist_and_positions(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_position: Position,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Full trading loop should process both watchlist and positions."""
        # Arrange
        second_stock = StockPrice(
            code="035720",
            name="Kakao",
            current_price=50000,
            change_rate=2.0,
            volume=5000000,
            high=51000,
            low=49000,
            open=49500,
        )
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price, second_stock]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD006",
            message="Order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="No risk trigger",
            current_profit_pct=7.69,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930", "035720"],
            positions=[sample_position],
        )

        # Assert
        assert result.processed_stocks >= 2
        assert result.signals_generated >= 1

    @pytest.mark.asyncio
    async def test_empty_watchlist_and_positions(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Trading loop should handle empty input gracefully."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[],
        )

        # Assert
        assert result.processed_stocks == 0
        assert result.signals_generated == 0
        assert result.orders_executed == 0
        assert result.alerts_sent == 0


class TestProcessBuySignal:
    """Test process_buy_signal method."""

    @pytest.mark.asyncio
    async def test_process_buy_signal_auto_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_buy_signal: TradingSignal,
    ):
        """Process buy signal should execute order in AUTO mode."""
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD007",
            message="Order placed",
            status=OrderStatus.PENDING,
        )
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        order_result = await engine.process_buy_signal(
            signal=sample_buy_signal,
            stock_code="005930",
            current_price=70000,
        )

        # Assert
        assert order_result is not None
        assert order_result.success is True

    @pytest.mark.asyncio
    async def test_process_buy_signal_alert_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_buy_signal: TradingSignal,
    ):
        """Process buy signal should return None and send alert in ALERT mode."""
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        order_result = await engine.process_buy_signal(
            signal=sample_buy_signal,
            stock_code="005930",
            current_price=70000,
        )

        # Assert
        assert order_result is None
        mock_kis_client.place_order.assert_not_called()


class TestProcessSellSignal:
    """Test process_sell_signal method."""

    @pytest.mark.asyncio
    async def test_process_sell_signal_auto_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_sell_signal: TradingSignal,
        sample_position: Position,
    ):
        """Process sell signal should execute order in AUTO mode."""
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD008",
            message="Order placed",
            status=OrderStatus.PENDING,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        order_result = await engine.process_sell_signal(
            signal=sample_sell_signal,
            position=sample_position,
        )

        # Assert
        assert order_result is not None
        assert order_result.success is True

    @pytest.mark.asyncio
    async def test_process_sell_signal_alert_mode(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_sell_signal: TradingSignal,
        sample_position: Position,
    ):
        """Process sell signal should return None and send alert in ALERT mode."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        order_result = await engine.process_sell_signal(
            signal=sample_sell_signal,
            position=sample_position,
        )

        # Assert
        assert order_result is None
        mock_kis_client.place_order.assert_not_called()


class TestCheckPositionRisk:
    """Test check_position_risk method."""

    @pytest.mark.asyncio
    async def test_check_position_risk_hold(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_position: Position,
    ):
        """Position within safe range should return HOLD."""
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="Position within safe range",
            current_profit_pct=5.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.check_position_risk(
            position=sample_position,
            trailing_stops={},
        )

        # Assert
        assert result.action == RiskAction.HOLD

    @pytest.mark.asyncio
    async def test_check_position_risk_with_trailing_stop(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_position: Position,
    ):
        """Position with active trailing stop should be checked properly."""
        trailing_stop = TrailingStop(entry_price=65000, trailing_pct=5.0)
        trailing_stop.update_price(75000)  # Highest price

        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.TRAILING_STOP,
            reason="Trailing stop triggered",
            current_profit_pct=7.69,
            trigger_price=71250.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.check_position_risk(
            position=sample_position,
            trailing_stops={"005930": trailing_stop},
        )

        # Assert
        assert result.action == RiskAction.TRAILING_STOP


class TestErrorHandling:
    """Test error handling in trading engine."""

    @pytest.mark.asyncio
    async def test_api_error_recorded_in_results(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """API errors should be recorded in TradingLoopResult.errors."""
        from app.services.kis_api import KISApiError

        mock_kis_client.get_stock_prices.side_effect = KISApiError("API connection failed")

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Assert
        assert len(result.errors) > 0
        assert "API" in result.errors[0] or "connection" in result.errors[0] or "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_order_failure_recorded(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Order failures should be recorded in errors."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_kis_client.place_order.return_value = OrderResult(
            success=False,
            order_id=None,
            message="Insufficient funds",
            status=OrderStatus.FAILED,
        )
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Assert
        assert result.orders_executed == 0


class TestPendingAlerts:
    """Test pending alert management."""

    @pytest.mark.asyncio
    async def test_get_pending_alerts_returns_list(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Pending alerts should be tracked and retrievable."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )
        pending = engine.get_pending_alerts()

        # Assert
        assert isinstance(pending, list)
        assert len(pending) >= 1

    @pytest.mark.asyncio
    async def test_approve_pending_alert_executes_order(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Approving a pending alert should execute the order."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD009",
            message="Order placed",
            status=OrderStatus.PENDING,
        )
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Generate pending alert
        await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )
        pending = engine.get_pending_alerts()
        assert len(pending) >= 1

        # Approve the first alert
        alert_id = pending[0].alert_id
        order_result = await engine.approve_alert(alert_id)

        # Assert
        assert order_result is not None
        assert order_result.success is True
        mock_kis_client.place_order.assert_called()

    @pytest.mark.asyncio
    async def test_reject_pending_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Rejecting a pending alert should remove it without executing."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 10_000_000}
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.can_open_position.return_value = (True, "")
        mock_risk_manager.calculate_position_size.return_value = 10

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Generate pending alert
        await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )
        pending = engine.get_pending_alerts()
        assert len(pending) >= 1

        # Reject the first alert
        alert_id = pending[0].alert_id
        engine.reject_alert(alert_id)

        # Assert
        new_pending = engine.get_pending_alerts()
        assert all(a.alert_id != alert_id for a in new_pending)
        mock_kis_client.place_order.assert_not_called()


class TestTrailingStopManagement:
    """Test trailing stop management."""

    @pytest.mark.asyncio
    async def test_trailing_stop_created_for_position(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_position: Position,
        sample_stock_price: StockPrice,
        sample_hold_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Trailing stop should be created for new positions."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_signal_generator.generate_signal.return_value = sample_hold_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="Position safe",
            current_profit_pct=7.69,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Act
        await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        # Assert - trailing stop should be tracked
        trailing_stops = engine.get_trailing_stops()
        assert "005930" in trailing_stops

    @pytest.mark.asyncio
    async def test_trailing_stop_updates_on_price_increase(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Trailing stop should update when price increases."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Create initial trailing stop
        engine._trailing_stops["005930"] = TrailingStop(
            entry_price=65000,
            trailing_pct=5.0,
        )

        # Update with higher price
        engine.update_trailing_stop("005930", 75000)

        # Assert
        trailing_stop = engine._trailing_stops["005930"]
        assert trailing_stop.highest_price == 75000
        assert trailing_stop.stop_price == 75000 * (1 - 5.0 / 100)


class TestEdgeCases:
    """Test edge cases and additional scenarios."""

    @pytest.mark.asyncio
    async def test_position_processing_error_recorded(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_position: Position,
    ):
        """Exception during position processing should be recorded in errors."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_risk_manager.check_position.side_effect = Exception("Database error")

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        assert len(result.errors) > 0
        assert "005930" in result.errors[0]

    @pytest.mark.asyncio
    async def test_watchlist_processing_error_logged(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
    ):
        """Exception during watchlist stock processing should be logged and handled."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.side_effect = Exception("Network error")

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Should complete without crashing, no signals generated due to error
        assert result.signals_generated == 0
        assert result.orders_executed == 0

    @pytest.mark.asyncio
    async def test_position_without_price_in_map(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_position: Position,
    ):
        """Position without price data should be skipped gracefully."""
        # Return empty price list
        mock_kis_client.get_stock_prices.return_value = []

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        # Should complete without error
        assert result.processed_stocks == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_approve_nonexistent_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Approving non-existent alert should return None."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.approve_alert("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_reject_nonexistent_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Rejecting non-existent alert should return False."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = engine.reject_alert("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_daily_pnl(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Daily PnL should be settable."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        engine.set_daily_pnl(-5.0)
        assert engine._daily_pnl_pct == -5.0

    @pytest.mark.asyncio
    async def test_clear_trailing_stops(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
    ):
        """Trailing stops should be clearable."""
        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        engine._trailing_stops["005930"] = TrailingStop(65000, 5.0)
        engine.clear_trailing_stops()
        assert len(engine._trailing_stops) == 0

    @pytest.mark.asyncio
    async def test_clear_pending_alerts(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_buy_signal: TradingSignal,
    ):
        """Pending alerts should be clearable."""
        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Add an alert manually
        engine._pending_alerts["test-id"] = AlertInfo(
            alert_id="test-id",
            stock_code="005930",
            signal=sample_buy_signal,
            signal_type=SignalType.BUY,
            current_price=70000,
            suggested_quantity=10,
        )

        engine.clear_pending_alerts()
        assert len(engine._pending_alerts) == 0

    @pytest.mark.asyncio
    async def test_approve_sell_alert(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_sell_signal: TradingSignal,
        sample_position: Position,
    ):
        """Approving sell alert should execute sell order."""
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD010",
            message="Sell order placed",
            status=OrderStatus.PENDING,
        )

        engine = TradingEngine(
            mode=TradingMode.ALERT,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Add a sell alert manually
        engine._pending_alerts["sell-alert-id"] = AlertInfo(
            alert_id="sell-alert-id",
            stock_code="005930",
            signal=sample_sell_signal,
            signal_type=SignalType.SELL,
            current_price=70000,
            suggested_quantity=10,
            position=sample_position,
        )

        result = await engine.approve_alert("sell-alert-id")

        assert result is not None
        assert result.success is True
        mock_kis_client.place_order.assert_called_with(
            stock_code="005930",
            side=OrderSide.SELL,
            quantity=10,
            price=None,
        )

    @pytest.mark.asyncio
    async def test_buy_signal_with_zero_position_size(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Buy signal with zero position size should not execute order."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.return_value = {"available_amount": 1000}
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.calculate_position_size.return_value = 0  # Zero quantity

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Should not execute order
        mock_kis_client.place_order.assert_not_called()
        assert result.orders_executed == 0

    @pytest.mark.asyncio
    async def test_balance_fetch_error_handled(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_buy_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Balance fetch error should be handled gracefully."""
        from app.services.kis_api import KISApiError

        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.get_balance.side_effect = KISApiError("Balance fetch failed")
        mock_signal_generator.generate_signal.return_value = sample_buy_signal
        mock_risk_manager.calculate_position_size.return_value = 0  # Will be 0 with no capital

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=["005930"],
            positions=[],
        )

        # Should complete without crashing
        assert result.signals_generated >= 1

    @pytest.mark.asyncio
    async def test_watchlist_stock_already_in_position(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_position: Position,
        sample_hold_signal: TradingSignal,
        sample_daily_prices: list[dict],
    ):
        """Watchlist stock that is already in position should be processed only once."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_signal_generator.generate_signal.return_value = sample_hold_signal
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.HOLD,
            reason="Position safe",
            current_profit_pct=7.69,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        result = await engine.run_trading_loop(
            watchlist=["005930"],  # Same as position
            positions=[sample_position],
        )

        # Should only process once as position, not as watchlist
        assert result.processed_stocks == 1
        assert mock_signal_generator.generate_signal.call_count == 1

    @pytest.mark.asyncio
    async def test_risk_triggered_sell_removes_trailing_stop(
        self,
        mock_kis_client: AsyncMock,
        mock_signal_generator: MagicMock,
        mock_risk_manager: MagicMock,
        sample_stock_price: StockPrice,
        sample_position: Position,
        sample_daily_prices: list[dict],
    ):
        """Successful risk-triggered sell should remove trailing stop."""
        mock_kis_client.get_stock_prices.return_value = [sample_stock_price]
        mock_kis_client.get_daily_prices.return_value = sample_daily_prices
        mock_kis_client.place_order.return_value = OrderResult(
            success=True,
            order_id="ORD011",
            message="Stop-loss order placed",
            status=OrderStatus.PENDING,
        )
        mock_risk_manager.check_position.return_value = RiskCheckResult(
            action=RiskAction.STOP_LOSS,
            reason="Stop-loss triggered",
            current_profit_pct=-7.0,
            trigger_price=61000.0,
        )

        engine = TradingEngine(
            mode=TradingMode.AUTO,
            kis_client=mock_kis_client,
            signal_generator=mock_signal_generator,
            risk_manager=mock_risk_manager,
        )

        # Pre-populate trailing stop
        engine._trailing_stops["005930"] = TrailingStop(65000, 5.0)

        await engine.run_trading_loop(
            watchlist=[],
            positions=[sample_position],
        )

        # Trailing stop should be removed after successful sell
        assert "005930" not in engine._trailing_stops
