"""Stock price and backtest models for Phase 4 backtesting."""

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StockPrice(Base):
    """Stock price daily OHLCV data for backtesting and analysis."""

    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    high_price: Mapped[float] = mapped_column(Float, nullable=False)
    low_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_stock_prices_code_date", "stock_code", "trade_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<StockPrice {self.stock_code} {self.trade_date}>"


class BacktestResult(Base):
    """Backtest result storage with configuration and metrics."""

    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821
    trades: Mapped[list["BacktestTrade"]] = relationship(
        "BacktestTrade", back_populates="backtest", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BacktestResult {self.id} {self.name}>"


class BacktestTrade(Base):
    """Individual simulated trade record from a backtest."""

    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtest_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, nullable=False)
    tax: Mapped[float] = mapped_column(Float, nullable=False)
    signal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)

    backtest: Mapped["BacktestResult"] = relationship(
        "BacktestResult", back_populates="trades", foreign_keys=[backtest_id]
    )

    def __repr__(self) -> str:
        return f"<BacktestTrade {self.trade_date} {self.stock_code} {self.side}>"
