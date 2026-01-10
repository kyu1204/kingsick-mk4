from datetime import date

import pytest

from app.services.backtest_engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    BacktestTrade,
    Position,
)


class TestBacktestConfig:
    def test_default_values(self):
        config = BacktestConfig()

        assert config.initial_capital == 10_000_000
        assert config.commission_rate == 0.00015
        assert config.tax_rate == 0.0023
        assert config.slippage == 0.001
        assert config.stop_loss_pct == 5.0
        assert config.take_profit_pct == 10.0
        assert config.max_position_pct == 20.0
        assert config.max_positions == 5

    def test_custom_values(self):
        config = BacktestConfig(
            initial_capital=50_000_000,
            commission_rate=0.0003,
            tax_rate=0.003,
            slippage=0.002,
            stop_loss_pct=3.0,
            take_profit_pct=15.0,
            max_position_pct=10.0,
            max_positions=10,
        )

        assert config.initial_capital == 50_000_000
        assert config.commission_rate == 0.0003
        assert config.max_positions == 10


class TestPosition:
    def test_unrealized_pnl_profit(self):
        position = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=55000.0,
        )

        assert position.unrealized_pnl == 50000.0

    def test_unrealized_pnl_loss(self):
        position = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=45000.0,
        )

        assert position.unrealized_pnl == -50000.0

    def test_unrealized_pnl_pct_profit(self):
        position = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=55000.0,
        )

        assert position.unrealized_pnl_pct == 10.0

    def test_unrealized_pnl_pct_loss(self):
        position = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=45000.0,
        )

        assert position.unrealized_pnl_pct == -10.0

    def test_unrealized_pnl_pct_zero_entry(self):
        position = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=0.0,
            quantity=10,
            current_price=50000.0,
        )

        assert position.unrealized_pnl_pct == 0.0


class TestBacktestTrade:
    def test_buy_trade(self):
        trade = BacktestTrade(
            trade_date=date(2025, 1, 15),
            stock_code="005930",
            side="BUY",
            price=50000.0,
            quantity=10,
            amount=500000.0,
            commission=75.0,
            tax=0.0,
            signal_reason="RSI oversold",
        )

        assert trade.side == "BUY"
        assert trade.pnl == 0.0
        assert trade.tax == 0.0

    def test_sell_trade_with_pnl(self):
        trade = BacktestTrade(
            trade_date=date(2025, 2, 15),
            stock_code="005930",
            side="SELL",
            price=55000.0,
            quantity=10,
            amount=550000.0,
            commission=82.5,
            tax=1265.0,
            signal_reason="Take profit",
            pnl=48652.5,
            pnl_pct=10.0,
        )

        assert trade.side == "SELL"
        assert trade.pnl == 48652.5
        assert trade.tax == 1265.0


class TestBacktestEngine:
    @pytest.fixture
    def engine(self) -> BacktestEngine:
        config = BacktestConfig(
            initial_capital=10_000_000,
            commission_rate=0.00015,
            tax_rate=0.0023,
            slippage=0.001,
            stop_loss_pct=5.0,
            take_profit_pct=10.0,
            max_position_pct=100.0,
            max_positions=1,
        )
        return BacktestEngine(config=config)

    @pytest.fixture
    def simple_price_data(self) -> dict[str, list[dict]]:
        from datetime import timedelta

        base_date = date(2025, 1, 1)
        prices = []
        for i in range(60):
            d = base_date + timedelta(days=i)
            prices.append(
                {
                    "date": d,
                    "open": 50000.0,
                    "high": 51000.0,
                    "low": 49000.0,
                    "close": 50000.0 + (i * 100),
                    "volume": 1000000,
                }
            )
        return {"005930": prices}

    def test_run_empty_data(self, engine: BacktestEngine):
        result = engine.run(
            price_data={},
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert result.total_trades == 0
        assert result.final_capital == engine.config.initial_capital
        assert result.total_return_pct == 0.0

    def test_run_returns_backtest_result(self, engine: BacktestEngine, simple_price_data):
        result = engine.run(
            price_data=simple_price_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 2, 28),
        )

        assert isinstance(result, BacktestResult)
        assert result.start_date == date(2025, 1, 1)
        assert result.end_date == date(2025, 2, 28)
        assert result.initial_capital == 10_000_000

    def test_equity_curve_tracking(self, engine: BacktestEngine, simple_price_data):
        result = engine.run(
            price_data=simple_price_data,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 2, 28),
        )

        assert len(result.daily_equity) > 0
        assert result.daily_equity[0] == engine.config.initial_capital

    def test_calculate_cagr(self, engine: BacktestEngine):
        cagr = engine._calculate_cagr(
            initial=10_000_000,
            final=11_000_000,
            years=1.0,
        )
        assert pytest.approx(cagr, abs=0.01) == 10.0

    def test_calculate_cagr_two_years(self, engine: BacktestEngine):
        cagr = engine._calculate_cagr(
            initial=10_000_000,
            final=12_100_000,
            years=2.0,
        )
        assert pytest.approx(cagr, abs=0.01) == 10.0

    def test_calculate_cagr_negative(self, engine: BacktestEngine):
        cagr = engine._calculate_cagr(
            initial=10_000_000,
            final=9_000_000,
            years=1.0,
        )
        assert cagr < 0

    def test_calculate_cagr_zero_initial(self, engine: BacktestEngine):
        cagr = engine._calculate_cagr(
            initial=0,
            final=10_000_000,
            years=1.0,
        )
        assert cagr == 0.0

    def test_calculate_mdd(self, engine: BacktestEngine):
        engine._equity_curve = [100, 110, 105, 120, 100, 130]
        mdd = engine._calculate_mdd()

        expected_mdd = ((120 - 100) / 120) * 100
        assert pytest.approx(mdd, abs=0.01) == expected_mdd

    def test_calculate_mdd_no_drawdown(self, engine: BacktestEngine):
        engine._equity_curve = [100, 110, 120, 130, 140]
        mdd = engine._calculate_mdd()
        assert mdd == 0.0

    def test_calculate_daily_returns(self, engine: BacktestEngine):
        engine._equity_curve = [100, 110, 105]
        returns = engine._calculate_daily_returns()

        assert len(returns) == 2
        assert pytest.approx(returns[0], abs=0.01) == 10.0
        assert pytest.approx(returns[1], abs=0.01) == -4.545

    def test_calculate_sharpe_ratio(self, engine: BacktestEngine):
        daily_returns = [0.1] * 252
        sharpe = engine._calculate_sharpe_ratio(daily_returns)

        assert sharpe > 0

    def test_calculate_sharpe_ratio_insufficient_data(self, engine: BacktestEngine):
        sharpe = engine._calculate_sharpe_ratio([1.0])
        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_zero_volatility(self, engine: BacktestEngine):
        sharpe = engine._calculate_sharpe_ratio([0.0, 0.0, 0.0])
        assert sharpe == 0.0


class TestBacktestEngineTrading:
    @pytest.fixture
    def engine(self) -> BacktestEngine:
        config = BacktestConfig(
            initial_capital=10_000_000,
            commission_rate=0.0,
            tax_rate=0.0,
            slippage=0.0,
            stop_loss_pct=5.0,
            take_profit_pct=10.0,
            max_position_pct=100.0,
            max_positions=5,
        )
        return BacktestEngine(config=config)

    def test_execute_buy(self, engine: BacktestEngine):
        engine._cash = 1_000_000
        engine._execute_buy("005930", date(2025, 1, 15), 50000.0, "Test signal")

        assert "005930" in engine._positions
        assert engine._positions["005930"].entry_price == 50000.0
        assert len(engine._trades) == 1
        assert engine._trades[0].side == "BUY"

    def test_execute_buy_insufficient_cash(self, engine: BacktestEngine):
        engine._cash = 1000
        engine._execute_buy("005930", date(2025, 1, 15), 50000.0, "Test signal")

        assert "005930" not in engine._positions
        assert len(engine._trades) == 0

    def test_execute_sell(self, engine: BacktestEngine):
        engine._cash = 0
        engine._positions["005930"] = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=55000.0,
        )

        engine._execute_sell("005930", date(2025, 1, 15), "Test exit")

        assert "005930" not in engine._positions
        assert engine._cash == 550000.0
        assert len(engine._trades) == 1
        assert engine._trades[0].side == "SELL"
        assert engine._trades[0].pnl == 50000.0

    def test_execute_sell_nonexistent_position(self, engine: BacktestEngine):
        engine._execute_sell("005930", date(2025, 1, 15), "Test exit")
        assert len(engine._trades) == 0

    def test_total_equity_cash_only(self, engine: BacktestEngine):
        engine._cash = 1_000_000
        engine._positions = {}

        assert engine._total_equity() == 1_000_000

    def test_total_equity_with_positions(self, engine: BacktestEngine):
        engine._cash = 500_000
        engine._positions["005930"] = Position(
            stock_code="005930",
            entry_date=date(2025, 1, 1),
            entry_price=50000.0,
            quantity=10,
            current_price=55000.0,
        )

        assert engine._total_equity() == 500_000 + (55000 * 10)


class TestBacktestResult:
    def test_result_attributes(self):
        result = BacktestResult(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            initial_capital=10_000_000,
            final_capital=11_000_000,
            total_return_pct=10.0,
            cagr=10.0,
            mdd=5.0,
            sharpe_ratio=1.5,
            win_rate=60.0,
            profit_factor=2.0,
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            avg_win=100000.0,
            avg_loss=-50000.0,
            max_win=200000.0,
            max_loss=-80000.0,
        )

        assert result.total_return_pct == 10.0
        assert result.win_rate == 60.0
        assert result.winning_trades == 12


class TestBacktestEngineMetrics:
    @pytest.fixture
    def engine(self) -> BacktestEngine:
        return BacktestEngine()

    def test_calculate_results_with_trades(self, engine: BacktestEngine):
        engine._cash = 10_500_000
        engine._equity_curve = [10_000_000, 10_200_000, 10_500_000]
        engine._trades = [
            BacktestTrade(
                trade_date=date(2025, 1, 10),
                stock_code="005930",
                side="BUY",
                price=50000.0,
                quantity=10,
                amount=500000.0,
                commission=75.0,
                tax=0.0,
                signal_reason="Buy signal",
            ),
            BacktestTrade(
                trade_date=date(2025, 1, 20),
                stock_code="005930",
                side="SELL",
                price=55000.0,
                quantity=10,
                amount=550000.0,
                commission=82.5,
                tax=1265.0,
                signal_reason="Sell signal",
                pnl=48652.5,
                pnl_pct=10.0,
            ),
        ]

        result = engine._calculate_results(date(2025, 1, 1), date(2025, 1, 31))

        assert result.final_capital == 10_500_000
        assert result.total_trades == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 0
        assert result.win_rate == 100.0

    def test_calculate_results_empty(self, engine: BacktestEngine):
        result = engine._calculate_results(date(2025, 1, 1), date(2025, 1, 31))

        assert result.total_trades == 0
        assert result.final_capital == engine.config.initial_capital
