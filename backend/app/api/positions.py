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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.schemas import (
    BalanceResponse,
    DailyPriceResponse,
    PositionListResponse,
    PositionSchema,
    StockPriceResponse,
)
from app.database import get_db
from app.models import User, UserApiKey
from app.services.encryption import decrypt
from app.services.kis_api import KISApiClient, KISApiError, Position
from app.services.kis_token_cache import get_authenticated_kis_client

router = APIRouter(prefix="/positions", tags=["positions"])


async def get_kis_client_for_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KISApiClient:
    """Dependency to get authenticated KIS API client for the current user."""
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == current_user.id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="KIS API credentials not configured. Please add your API key in Settings.",
        )

    try:
        app_key = decrypt(api_key.kis_app_key_encrypted)
        app_secret = decrypt(api_key.kis_app_secret_encrypted)
        account_no = decrypt(api_key.kis_account_no_encrypted)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decrypt API credentials: {e}",
        )

    try:
        return await get_authenticated_kis_client(
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            is_mock=api_key.is_paper_trading,
        )
    except KISApiError as e:
        raise HTTPException(status_code=502, detail=str(e))


async def get_positions_from_api(client: KISApiClient) -> list[Position]:
    """Helper function to get positions from KIS API."""
    return await client.get_positions()


@router.get("/", response_model=PositionListResponse)
async def get_positions(
    client: Annotated[KISApiClient, Depends(get_kis_client_for_user)],
) -> PositionListResponse:
    try:
        async with client:
            positions = await client.get_positions()

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
    client: Annotated[KISApiClient, Depends(get_kis_client_for_user)],
) -> BalanceResponse:
    try:
        async with client:
            balance = await client.get_balance()

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
    client: Annotated[KISApiClient, Depends(get_kis_client_for_user)],
) -> StockPriceResponse:
    try:
        async with client:
            price = await client.get_stock_price(stock_code)

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
    client: Annotated[KISApiClient, Depends(get_kis_client_for_user)],
    count: int = Query(default=100, ge=1, le=500, description="Number of days to retrieve"),
) -> list[DailyPriceResponse]:
    try:
        async with client:
            daily_prices = await client.get_daily_prices(stock_code, count)

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
