"""
Pydantic schemas for API request/response models.

Provides data validation and serialization for REST API endpoints.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# Enums
class SignalTypeEnum(str, Enum):
    """Trading signal types."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingModeEnum(str, Enum):
    """Trading mode types."""

    AUTO = "AUTO"
    ALERT = "ALERT"


class RiskActionEnum(str, Enum):
    """Risk action types."""

    HOLD = "HOLD"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderSideEnum(str, Enum):
    """Order side types."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatusEnum(str, Enum):
    """Order status types."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# Indicator Schemas
class SMARequest(BaseModel):
    """Request schema for SMA calculation."""

    prices: list[float] = Field(..., description="List of price values")
    period: int = Field(..., gt=0, description="SMA period")


class SMAResponse(BaseModel):
    """Response schema for SMA calculation."""

    values: list[float | None] = Field(..., description="Calculated SMA values (None for NaN)")


class EMARequest(BaseModel):
    """Request schema for EMA calculation."""

    prices: list[float] = Field(..., description="List of price values")
    period: int = Field(..., gt=0, description="EMA period")


class EMAResponse(BaseModel):
    """Response schema for EMA calculation."""

    values: list[float | None] = Field(..., description="Calculated EMA values (None for NaN)")


class RSIRequest(BaseModel):
    """Request schema for RSI calculation."""

    prices: list[float] = Field(..., description="List of price values")
    period: int = Field(14, gt=0, description="RSI period")


class RSIResponse(BaseModel):
    """Response schema for RSI calculation."""

    values: list[float | None] = Field(..., description="Calculated RSI values (None for NaN)")


class MACDRequest(BaseModel):
    """Request schema for MACD calculation."""

    prices: list[float] = Field(..., description="List of price values")
    fast: int = Field(12, gt=0, description="Fast EMA period")
    slow: int = Field(26, gt=0, description="Slow EMA period")
    signal: int = Field(9, gt=0, description="Signal line period")


class MACDResponse(BaseModel):
    """Response schema for MACD calculation."""

    macd_line: list[float | None] = Field(..., description="MACD line values")
    signal_line: list[float | None] = Field(..., description="Signal line values")
    histogram: list[float | None] = Field(..., description="Histogram values")


class BollingerBandsRequest(BaseModel):
    """Request schema for Bollinger Bands calculation."""

    prices: list[float] = Field(..., description="List of price values")
    period: int = Field(20, gt=0, description="SMA period")
    std_dev: float = Field(2.0, gt=0, description="Standard deviation multiplier")


class BollingerBandsResponse(BaseModel):
    """Response schema for Bollinger Bands calculation."""

    upper: list[float | None] = Field(..., description="Upper band values")
    middle: list[float | None] = Field(..., description="Middle band values")
    lower: list[float | None] = Field(..., description="Lower band values")


class VolumeSpikeRequest(BaseModel):
    """Request schema for volume spike detection."""

    volumes: list[float] = Field(..., description="List of volume values")
    threshold: float = Field(2.0, gt=0, description="Spike threshold multiplier")
    lookback: int = Field(20, gt=0, description="Lookback period")


class VolumeSpikeResponse(BaseModel):
    """Response schema for volume spike detection."""

    spikes: list[bool] = Field(..., description="Boolean values indicating spike presence")


class CrossDetectionRequest(BaseModel):
    """Request schema for golden/death cross detection."""

    prices: list[float] = Field(..., description="List of price values")
    short_period: int = Field(5, gt=0, description="Short MA period")
    long_period: int = Field(20, gt=0, description="Long MA period")


class CrossDetectionResponse(BaseModel):
    """Response schema for cross detection."""

    detected: bool = Field(..., description="Whether cross was detected")


# Signal Schemas
class GenerateSignalRequest(BaseModel):
    """Request schema for signal generation."""

    prices: list[float] = Field(..., description="List of historical price values")
    volumes: list[float] = Field(..., description="List of historical volume values")


class TradingSignalResponse(BaseModel):
    """Response schema for trading signal."""

    signal: SignalTypeEnum = Field(..., description="Signal type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reason: str = Field(..., description="Signal reason")
    indicators: dict = Field(default_factory=dict, description="Calculated indicators")


# Position Schemas
class PositionSchema(BaseModel):
    """Schema for position data."""

    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    quantity: int = Field(..., description="Number of shares")
    avg_price: float = Field(..., description="Average purchase price")
    current_price: float = Field(..., description="Current market price")
    profit_loss: float = Field(..., description="Profit/loss amount")
    profit_loss_rate: float = Field(..., description="Profit/loss percentage")


class PositionListResponse(BaseModel):
    """Response schema for position list."""

    positions: list[PositionSchema] = Field(..., description="List of positions")


class BalanceResponse(BaseModel):
    """Response schema for account balance."""

    deposit: float = Field(..., description="Total deposit amount")
    available_amount: float = Field(..., description="Available amount for trading")
    total_evaluation: float = Field(..., description="Total portfolio evaluation")
    net_worth: float = Field(..., description="Net asset value")
    purchase_amount: float = Field(..., description="Total purchase amount")
    evaluation_amount: float = Field(..., description="Total stock evaluation amount")


# Risk Schemas
class RiskCheckRequest(BaseModel):
    """Request schema for position risk check."""

    entry_price: float = Field(..., gt=0, description="Entry price")
    current_price: float = Field(..., gt=0, description="Current price")
    trailing_stop_price: float | None = Field(None, description="Optional trailing stop price")


class RiskCheckResponse(BaseModel):
    """Response schema for risk check."""

    action: RiskActionEnum = Field(..., description="Recommended action")
    reason: str = Field(..., description="Action reason")
    current_profit_pct: float = Field(..., description="Current profit/loss percentage")
    trigger_price: float | None = Field(None, description="Trigger price if applicable")


class PositionSizeRequest(BaseModel):
    """Request schema for position size calculation."""

    available_capital: float = Field(..., gt=0, description="Available capital")
    stock_price: float = Field(..., gt=0, description="Stock price")
    risk_per_trade_pct: float = Field(2.0, gt=0, le=100, description="Risk per trade percentage")


class PositionSizeResponse(BaseModel):
    """Response schema for position size calculation."""

    quantity: int = Field(..., description="Recommended quantity")


class CanOpenPositionRequest(BaseModel):
    """Request schema for position opening check."""

    investment_amount: float = Field(..., gt=0, description="Investment amount")
    current_positions_count: int = Field(..., ge=0, description="Current position count")
    daily_pnl_pct: float = Field(..., description="Daily P&L percentage")


class CanOpenPositionResponse(BaseModel):
    """Response schema for position opening check."""

    can_open: bool = Field(..., description="Whether position can be opened")
    reason: str = Field("", description="Reason if cannot open")


# Trading Schemas
class OrderRequest(BaseModel):
    """Request schema for order placement."""

    stock_code: str = Field(..., description="Stock code")
    side: OrderSideEnum = Field(..., description="Order side")
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: float | None = Field(None, description="Limit price (None for market order)")


class OrderResponse(BaseModel):
    """Response schema for order result."""

    success: bool = Field(..., description="Whether order was successful")
    order_id: str | None = Field(None, description="Order ID if successful")
    message: str = Field(..., description="Result message")
    status: OrderStatusEnum = Field(..., description="Order status")


class TradingStatusResponse(BaseModel):
    """Response schema for trading status."""

    mode: TradingModeEnum = Field(..., description="Current trading mode")
    pending_alerts_count: int = Field(..., description="Number of pending alerts")
    trailing_stops_count: int = Field(..., description="Number of active trailing stops")


class SetModeRequest(BaseModel):
    """Request schema for setting trading mode."""

    mode: TradingModeEnum = Field(..., description="Trading mode to set")


class AlertSchema(BaseModel):
    """Schema for alert data."""

    alert_id: str = Field(..., description="Alert ID")
    stock_code: str = Field(..., description="Stock code")
    signal_type: SignalTypeEnum = Field(..., description="Signal type")
    confidence: float = Field(..., description="Signal confidence")
    reason: str = Field(..., description="Signal reason")
    current_price: float = Field(..., description="Current price")
    suggested_quantity: int = Field(..., description="Suggested quantity")
    created_at: datetime = Field(..., description="Alert creation time")


class AlertListResponse(BaseModel):
    """Response schema for alert list."""

    alerts: list[AlertSchema] = Field(..., description="List of pending alerts")


class ApproveAlertRequest(BaseModel):
    """Request schema for alert approval."""

    alert_id: str = Field(..., description="Alert ID to approve")


class RejectAlertRequest(BaseModel):
    """Request schema for alert rejection."""

    alert_id: str = Field(..., description="Alert ID to reject")


class TradingLoopResultResponse(BaseModel):
    """Response schema for trading loop result."""

    processed_stocks: int = Field(..., description="Number of stocks processed")
    signals_generated: int = Field(..., description="Number of signals generated")
    orders_executed: int = Field(..., description="Number of orders executed")
    alerts_sent: int = Field(..., description="Number of alerts sent")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")


class RunTradingLoopRequest(BaseModel):
    """Request schema for running trading loop."""

    watchlist: list[str] = Field(default_factory=list, description="Stock codes to watch")


# Stock Price Schemas
class StockPriceResponse(BaseModel):
    """Response schema for stock price."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    current_price: float = Field(..., description="Current price")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    change_rate: float = Field(..., description="Change rate")
    volume: int = Field(..., description="Trading volume")


class DailyPriceResponse(BaseModel):
    """Response schema for daily price data."""

    date: str = Field(..., description="Date")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: int = Field(..., description="Volume")


# Error Schemas
class ErrorResponse(BaseModel):
    """Response schema for errors."""

    detail: str = Field(..., description="Error message")
