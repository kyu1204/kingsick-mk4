"""Backtest API router for historical data and backtesting."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.price_history import PriceHistoryError, PriceHistoryService

router = APIRouter(prefix="/backtest", tags=["Backtest"])


class PriceSyncRequest(BaseModel):
    stock_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    days: int = Field(100, ge=1, le=365)


class PriceSyncResponse(BaseModel):
    stock_code: str
    synced_count: int
    message: str


class StockPriceResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceListResponse(BaseModel):
    stock_code: str
    start_date: str
    end_date: str
    count: int
    prices: list[StockPriceResponse]


@router.post("/prices/sync", response_model=PriceSyncResponse)
async def sync_stock_prices(
    request: PriceSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PriceSyncResponse:
    service = PriceHistoryService(db, kis_client=None)

    try:
        synced_count = await service.fetch_and_store(
            stock_code=request.stock_code,
            days=request.days,
        )
    except PriceHistoryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return PriceSyncResponse(
        stock_code=request.stock_code,
        synced_count=synced_count,
        message=f"Synced {synced_count} price records",
    )


@router.get("/prices/{stock_code}", response_model=PriceListResponse)
async def get_stock_prices(
    stock_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
) -> PriceListResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    service = PriceHistoryService(db)
    prices = await service.get_prices(stock_code, start_date, end_date)

    return PriceListResponse(
        stock_code=stock_code,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        count=len(prices),
        prices=[
            StockPriceResponse(
                date=p.trade_date.isoformat(),
                open=p.open_price,
                high=p.high_price,
                low=p.low_price,
                close=p.close_price,
                volume=p.volume,
            )
            for p in prices
        ],
    )


@router.post("/prices/{stock_code}/sync-latest", response_model=PriceSyncResponse)
async def sync_latest_prices(
    stock_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PriceSyncResponse:
    service = PriceHistoryService(db, kis_client=None)

    try:
        synced_count = await service.sync_latest(stock_code)
    except PriceHistoryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return PriceSyncResponse(
        stock_code=stock_code,
        synced_count=synced_count,
        message=f"Synced {synced_count} new price records",
    )
