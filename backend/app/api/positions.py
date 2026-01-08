"""
API router for position management.

Provides endpoints for:
- Getting current positions
- Account balance information
- Stock price queries
- Daily price data for analysis
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    BalanceResponse,
    DailyPriceResponse,
    PositionListResponse,
    PositionSchema,
    StockPriceResponse,
)
from app.config import get_settings
from app.services.kis_api import KISApiClient, KISApiError, Position

router = APIRouter(prefix="/positions", tags=["positions"])


def get_kis_client() -> KISApiClient | None:
    """
    Dependency to get KIS API client.

    Returns None if credentials are not configured.
    """
    settings = get_settings()
    if not settings.kis_app_key or not settings.kis_app_secret:
        return None

    return KISApiClient(
        app_key=settings.kis_app_key,
        app_secret=settings.kis_app_secret,
        account_no=settings.kis_account_no,
        is_mock=settings.kis_is_mock,
    )


async def get_positions_from_api(client: KISApiClient) -> list[Position]:
    """Helper function to get positions from KIS API."""
    return await client.get_positions()


def _check_client(client: KISApiClient | None) -> None:
    """Check if KIS client is available and raise HTTPException if not."""
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="KIS API credentials not configured",
        )


@router.get("/", response_model=PositionListResponse)
async def get_positions(
    client: Annotated[KISApiClient | None, Depends(get_kis_client)],
) -> PositionListResponse:
    """
    Get all current stock positions.

    Returns:
        PositionListResponse with list of positions

    Raises:
        HTTPException: If KIS API is not configured or API error occurs
    """
    _check_client(client)

    try:
        async with client:  # type: ignore
            await client.authenticate()  # type: ignore
            positions = await client.get_positions()  # type: ignore

            return PositionListResponse(
                positions=[
                    PositionSchema(
                        stock_code=p.stock_code,
                        stock_name=p.stock_name,
                        quantity=p.quantity,
                        avg_price=p.avg_price,
                        current_price=p.current_price,
                        profit_loss=p.profit_loss,
                        profit_loss_rate=p.profit_loss_rate,
                    )
                    for p in positions
                ]
            )
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    client: Annotated[KISApiClient | None, Depends(get_kis_client)],
) -> BalanceResponse:
    """
    Get account balance information.

    Returns:
        BalanceResponse with account balance details

    Raises:
        HTTPException: If KIS API is not configured or API error occurs
    """
    _check_client(client)

    try:
        async with client:  # type: ignore
            await client.authenticate()  # type: ignore
            balance = await client.get_balance()  # type: ignore

            return BalanceResponse(
                deposit=balance.get("deposit", 0.0),
                available_amount=balance.get("available_amount", 0.0),
                total_evaluation=balance.get("total_evaluation", 0.0),
                net_worth=balance.get("net_worth", 0.0),
                purchase_amount=balance.get("purchase_amount", 0.0),
                evaluation_amount=balance.get("evaluation_amount", 0.0),
            )
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/price/{stock_code}", response_model=StockPriceResponse)
async def get_stock_price(
    stock_code: str,
    client: Annotated[KISApiClient | None, Depends(get_kis_client)],
) -> StockPriceResponse:
    """
    Get current stock price.

    Args:
        stock_code: Stock code (e.g., "005930" for Samsung Electronics)
        client: KIS API client

    Returns:
        StockPriceResponse with current price data

    Raises:
        HTTPException: If KIS API is not configured or API error occurs
    """
    _check_client(client)

    try:
        async with client:  # type: ignore
            await client.authenticate()  # type: ignore
            price = await client.get_stock_price(stock_code)  # type: ignore

            return StockPriceResponse(
                code=price.code,
                name=price.name,
                current_price=price.current_price,
                open=price.open,
                high=price.high,
                low=price.low,
                change_rate=price.change_rate,
                volume=price.volume,
            )
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/daily-prices/{stock_code}", response_model=list[DailyPriceResponse])
async def get_daily_prices(
    stock_code: str,
    client: Annotated[KISApiClient | None, Depends(get_kis_client)],
    count: int = Query(default=100, ge=1, le=500, description="Number of days to retrieve"),
) -> list[DailyPriceResponse]:
    """
    Get daily OHLCV data for a stock.

    Args:
        stock_code: Stock code (e.g., "005930" for Samsung Electronics)
        client: KIS API client
        count: Number of days to retrieve (default: 100, max: 500)

    Returns:
        List of DailyPriceResponse with historical price data

    Raises:
        HTTPException: If KIS API is not configured or API error occurs
    """
    _check_client(client)

    try:
        async with client:  # type: ignore
            await client.authenticate()  # type: ignore
            daily_prices = await client.get_daily_prices(stock_code, count)  # type: ignore

            return [
                DailyPriceResponse(
                    date=str(dp.get("date", "")),
                    open=float(dp.get("open", 0)),
                    high=float(dp.get("high", 0)),
                    low=float(dp.get("low", 0)),
                    close=float(dp.get("close", 0)),
                    volume=int(dp.get("volume", 0)),
                )
                for dp in daily_prices
            ]
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
