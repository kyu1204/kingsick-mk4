"""
API router for trade history.

Provides endpoints for:
- Getting trade history
- Getting trade details
"""


from fastapi import APIRouter, Query
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


_mock_trades: list[TradeSchema] = []


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
