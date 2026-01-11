"""Backtest API router for historical data and backtesting."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.dependencies import get_kis_client_for_user
from app.database import get_db
from app.models import User
from app.models.backtest import BacktestResult as BacktestResultModel
from app.models.backtest import BacktestTrade as BacktestTradeModel
from app.services.backtest_engine import BacktestConfig, BacktestEngine
from app.services.kis_api import KISApiClient
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


class BacktestRunRequest(BaseModel):
    stock_codes: list[str] = Field(..., min_length=1, max_length=20)
    start_date: date
    end_date: date
    name: str | None = Field(None, max_length=100)
    initial_capital: float = Field(10_000_000, ge=1_000_000, le=1_000_000_000)
    stop_loss_pct: float = Field(5.0, ge=0.1, le=50.0)
    take_profit_pct: float = Field(10.0, ge=0.1, le=100.0)
    max_position_pct: float = Field(20.0, ge=5.0, le=100.0)
    max_positions: int = Field(5, ge=1, le=20)


class BacktestTradeResponse(BaseModel):
    trade_date: str
    stock_code: str
    side: str
    price: float
    quantity: int
    amount: float
    commission: float
    tax: float
    signal_reason: str
    pnl: float = 0.0
    pnl_pct: float = 0.0


class BacktestResultResponse(BaseModel):
    id: str
    name: str | None
    start_date: str
    end_date: str
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
    created_at: str | None = None
    trades: list[BacktestTradeResponse] = []
    daily_equity: list[float] = []
    daily_returns: list[float] = []
    drawdown_curve: list[float] = []


class BacktestListItem(BaseModel):
    id: str
    name: str | None
    start_date: str
    end_date: str
    total_return_pct: float
    sharpe_ratio: float
    total_trades: int
    created_at: str


class BacktestListResponse(BaseModel):
    count: int
    results: list[BacktestListItem]


@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest(
    request: BacktestRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    kis_client: Annotated[KISApiClient, Depends(get_kis_client_for_user)],
) -> BacktestResultResponse:
    if request.start_date >= request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    price_service = PriceHistoryService(db, kis_client=kis_client)

    price_data: dict[str, list[dict[str, object]]] = {}
    for stock_code in request.stock_codes:
        prices = await price_service.get_prices(stock_code, request.start_date, request.end_date)

        # If no prices found, try to sync from KIS API
        if not prices:
            try:
                days_to_fetch = (request.end_date - request.start_date).days + 30
                days_to_fetch = min(days_to_fetch, 365)
                await price_service.fetch_and_store(stock_code, days=days_to_fetch)
                prices = await price_service.get_prices(
                    stock_code, request.start_date, request.end_date
                )
            except PriceHistoryError:
                # If sync fails, continue without this stock
                pass

        if prices:
            price_data[stock_code] = [
                {
                    "date": p.trade_date,
                    "open": p.open_price,
                    "high": p.high_price,
                    "low": p.low_price,
                    "close": p.close_price,
                    "volume": p.volume,
                }
                for p in prices
            ]

    if not price_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No price data found for the specified stocks and date range. Please check the stock codes and date range.",
        )

    config = BacktestConfig(
        initial_capital=request.initial_capital,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        max_position_pct=request.max_position_pct,
        max_positions=request.max_positions,
    )

    engine = BacktestEngine(config=config)
    result = engine.run(price_data, request.start_date, request.end_date)

    config_dict = {
        "stock_codes": request.stock_codes,
        "initial_capital": config.initial_capital,
        "commission_rate": config.commission_rate,
        "tax_rate": config.tax_rate,
        "slippage": config.slippage,
        "stop_loss_pct": config.stop_loss_pct,
        "take_profit_pct": config.take_profit_pct,
        "max_position_pct": config.max_position_pct,
        "max_positions": config.max_positions,
    }

    result_dict = {
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_return_pct": result.total_return_pct,
        "cagr": result.cagr,
        "mdd": result.mdd,
        "sharpe_ratio": result.sharpe_ratio,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "max_win": result.max_win,
        "max_loss": result.max_loss,
        "daily_equity": result.daily_equity,
        "daily_returns": result.daily_returns,
        "drawdown_curve": result.drawdown_curve,
    }

    db_result = BacktestResultModel(
        user_id=current_user.id,
        name=request.name,
        config=config_dict,
        result=result_dict,
    )
    db.add(db_result)
    await db.flush()

    for trade in result.trades:
        db_trade = BacktestTradeModel(
            backtest_id=db_result.id,
            trade_date=trade.trade_date,
            stock_code=trade.stock_code,
            side=trade.side,
            price=trade.price,
            quantity=trade.quantity,
            amount=trade.amount,
            commission=trade.commission,
            tax=trade.tax,
            signal_reason=trade.signal_reason,
            pnl=trade.pnl,
            pnl_pct=trade.pnl_pct,
        )
        db.add(db_trade)

    await db.commit()
    await db.refresh(db_result)

    return BacktestResultResponse(
        id=str(db_result.id),
        name=db_result.name,
        start_date=result.start_date.isoformat(),
        end_date=result.end_date.isoformat(),
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        total_return_pct=result.total_return_pct,
        cagr=result.cagr,
        mdd=result.mdd,
        sharpe_ratio=result.sharpe_ratio,
        win_rate=result.win_rate,
        profit_factor=result.profit_factor,
        total_trades=result.total_trades,
        winning_trades=result.winning_trades,
        losing_trades=result.losing_trades,
        avg_win=result.avg_win,
        avg_loss=result.avg_loss,
        max_win=result.max_win,
        max_loss=result.max_loss,
        created_at=db_result.created_at.isoformat() if db_result.created_at else None,
        trades=[
            BacktestTradeResponse(
                trade_date=t.trade_date.isoformat(),
                stock_code=t.stock_code,
                side=t.side,
                price=t.price,
                quantity=t.quantity,
                amount=t.amount,
                commission=t.commission,
                tax=t.tax,
                signal_reason=t.signal_reason,
                pnl=t.pnl,
                pnl_pct=t.pnl_pct,
            )
            for t in result.trades
        ],
        daily_equity=result.daily_equity,
        daily_returns=result.daily_returns,
        drawdown_curve=result.drawdown_curve,
    )


@router.get("/results", response_model=BacktestListResponse)
async def list_backtest_results(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BacktestListResponse:
    stmt = (
        select(BacktestResultModel)
        .where(BacktestResultModel.user_id == current_user.id)
        .order_by(BacktestResultModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    results = await db.execute(stmt)
    db_results = results.scalars().all()

    return BacktestListResponse(
        count=len(db_results),
        results=[
            BacktestListItem(
                id=str(r.id),
                name=r.name,
                start_date=r.result.get("start_date", ""),
                end_date=r.result.get("end_date", ""),
                total_return_pct=r.result.get("total_return_pct", 0.0),
                sharpe_ratio=r.result.get("sharpe_ratio", 0.0),
                total_trades=r.result.get("total_trades", 0),
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in db_results
        ],
    )


@router.get("/results/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest_result(
    backtest_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BacktestResultResponse:
    try:
        bt_uuid = uuid.UUID(backtest_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backtest ID format",
        ) from e

    stmt = select(BacktestResultModel).where(
        BacktestResultModel.id == bt_uuid,
        BacktestResultModel.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    db_result = result.scalar_one_or_none()

    if db_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found",
        )

    trades_stmt = (
        select(BacktestTradeModel)
        .where(BacktestTradeModel.backtest_id == bt_uuid)
        .order_by(BacktestTradeModel.trade_date)
    )
    trades_result = await db.execute(trades_stmt)
    db_trades = trades_result.scalars().all()

    r = db_result.result
    return BacktestResultResponse(
        id=str(db_result.id),
        name=db_result.name,
        start_date=r.get("start_date", ""),
        end_date=r.get("end_date", ""),
        initial_capital=r.get("initial_capital", 0.0),
        final_capital=r.get("final_capital", 0.0),
        total_return_pct=r.get("total_return_pct", 0.0),
        cagr=r.get("cagr", 0.0),
        mdd=r.get("mdd", 0.0),
        sharpe_ratio=r.get("sharpe_ratio", 0.0),
        win_rate=r.get("win_rate", 0.0),
        profit_factor=r.get("profit_factor", 0.0),
        total_trades=r.get("total_trades", 0),
        winning_trades=r.get("winning_trades", 0),
        losing_trades=r.get("losing_trades", 0),
        avg_win=r.get("avg_win", 0.0),
        avg_loss=r.get("avg_loss", 0.0),
        max_win=r.get("max_win", 0.0),
        max_loss=r.get("max_loss", 0.0),
        created_at=db_result.created_at.isoformat() if db_result.created_at else None,
        trades=[
            BacktestTradeResponse(
                trade_date=t.trade_date.isoformat(),
                stock_code=t.stock_code,
                side=t.side,
                price=t.price,
                quantity=t.quantity,
                amount=t.amount,
                commission=t.commission,
                tax=t.tax,
                signal_reason=t.signal_reason or "",
                pnl=t.pnl or 0.0,
                pnl_pct=t.pnl_pct or 0.0,
            )
            for t in db_trades
        ],
        daily_equity=r.get("daily_equity", []),
        daily_returns=r.get("daily_returns", []),
        drawdown_curve=r.get("drawdown_curve", []),
    )


@router.delete("/results/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest_result(
    backtest_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        bt_uuid = uuid.UUID(backtest_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backtest ID format",
        ) from e

    stmt = select(BacktestResultModel).where(
        BacktestResultModel.id == bt_uuid,
        BacktestResultModel.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    db_result = result.scalar_one_or_none()

    if db_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found",
        )

    await db.delete(db_result)
    await db.commit()
