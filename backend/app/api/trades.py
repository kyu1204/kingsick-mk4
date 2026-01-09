"""
API router for trade history.

Provides endpoints for:
- Getting trade history
- Getting trade details
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/trades", tags=["trades"])


class TradeSchema(BaseModel):
    """Schema for trade data."""

    id: int = Field(..., description="Trade ID")
    date: str = Field(..., description="Trade date and time")
    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    trade_type: str = Field(..., description="Trade type (BUY/SELL)")
    quantity: int = Field(..., description="Trade quantity")
    price: float = Field(..., description="Trade price")
    total: float = Field(..., description="Total trade value")
    status: str = Field(..., description="Trade status")
    signal_reason: str | None = Field(None, description="AI signal reason")


class TradeListResponse(BaseModel):
    """Response schema for trade list."""

    trades: list[TradeSchema] = Field(..., description="List of trades")
    total_count: int = Field(..., description="Total number of trades")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Number of items per page")


# Mock trade history data
_mock_trades = [
    TradeSchema(
        id=1,
        date="2024-01-15 14:23:45",
        stock_code="005930",
        stock_name="Samsung Electronics",
        trade_type="BUY",
        quantity=100,
        price=71000,
        total=7100000,
        status="completed",
        signal_reason="RSI oversold (28.5) + Golden cross detected",
    ),
    TradeSchema(
        id=2,
        date="2024-01-15 10:15:22",
        stock_code="000660",
        stock_name="SK Hynix",
        trade_type="SELL",
        quantity=50,
        price=186500,
        total=9325000,
        status="completed",
        signal_reason="Take profit triggered at +8.2%",
    ),
    TradeSchema(
        id=3,
        date="2024-01-14 15:28:11",
        stock_code="035420",
        stock_name="NAVER",
        trade_type="BUY",
        quantity=30,
        price=213000,
        total=6390000,
        status="completed",
        signal_reason="MACD bullish crossover + Volume spike (2.3x)",
    ),
    TradeSchema(
        id=4,
        date="2024-01-14 09:31:05",
        stock_code="035720",
        stock_name="Kakao",
        trade_type="BUY",
        quantity=200,
        price=55000,
        total=11000000,
        status="completed",
        signal_reason="Price near lower Bollinger band + RSI oversold",
    ),
    TradeSchema(
        id=5,
        date="2024-01-13 14:45:33",
        stock_code="006400",
        stock_name="Samsung SDI",
        trade_type="BUY",
        quantity=30,
        price=420000,
        total=12600000,
        status="completed",
        signal_reason="Strong uptrend + Volume confirmation",
    ),
    TradeSchema(
        id=6,
        date="2024-01-12 11:20:15",
        stock_code="005380",
        stock_name="Hyundai Motor",
        trade_type="SELL",
        quantity=80,
        price=245000,
        total=19600000,
        status="completed",
        signal_reason="Stop loss triggered at -3.2%",
    ),
    TradeSchema(
        id=7,
        date="2024-01-11 16:05:42",
        stock_code="051910",
        stock_name="LG Chem",
        trade_type="BUY",
        quantity=25,
        price=520000,
        total=13000000,
        status="completed",
        signal_reason="RSI divergence + Support level bounce",
    ),
]


@router.get("/", response_model=TradeListResponse)
async def get_trades(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
) -> TradeListResponse:
    """
    Get trade history with pagination.

    Args:
        page: Page number (default: 1)
        page_size: Number of items per page (default: 10, max: 100)

    Returns:
        TradeListResponse with paginated trade list
    """
    total_count = len(_mock_trades)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    return TradeListResponse(
        trades=_mock_trades[start_idx:end_idx],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/{trade_id}", response_model=TradeSchema)
async def get_trade(trade_id: int) -> TradeSchema:
    """
    Get a specific trade by ID.

    Args:
        trade_id: Trade ID

    Returns:
        TradeSchema with trade details

    Raises:
        HTTPException: If trade not found
    """
    from fastapi import HTTPException

    for trade in _mock_trades:
        if trade.id == trade_id:
            return trade

    raise HTTPException(status_code=404, detail="Trade not found")
