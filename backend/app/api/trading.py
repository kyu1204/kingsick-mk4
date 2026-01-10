"""
API router for trading operations.

Provides endpoints for:
- Trading mode management (AUTO/ALERT)
- Alert approval/rejection
- Risk management checks
- Position sizing
- Watchlist trading targets
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.schemas import (
    AlertListResponse,
    AlertSchema,
    ApproveAlertRequest,
    CanOpenPositionRequest,
    CanOpenPositionResponse,
    OrderResponse,
    OrderStatusEnum,
    PositionSizeRequest,
    PositionSizeResponse,
    RejectAlertRequest,
    RiskActionEnum,
    RiskCheckRequest,
    RiskCheckResponse,
    RiskSettingsRequest,
    RiskSettingsResponse,
    SetModeRequest,
    SignalTypeEnum,
    TradingModeEnum,
    TradingStatusResponse,
)
from app.database import get_db
from app.models import User
from app.services.risk_manager import RiskAction, RiskManager
from app.services.watchlist import WatchlistService

router = APIRouter(prefix="/trading", tags=["trading"])


# Watchlist trading targets response schema
class TradingTargetsResponse(BaseModel):
    """Response for trading targets from watchlist."""

    stock_codes: list[str]
    total: int


class TradingSettingsResponse(BaseModel):
    """Response for trading settings from watchlist."""

    target_price: float | None
    stop_loss_price: float | None
    quantity: int | None


# Global trading state (in production, this would be in a database or session)
class RiskSettings:
    """Risk settings for trading."""

    def __init__(self) -> None:
        self.stop_loss_pct: float = -5.0
        self.take_profit_pct: float = 10.0
        self.daily_loss_limit_pct: float = -10.0


class TradingState:
    """Simple in-memory trading state for demo purposes."""

    def __init__(self) -> None:
        self.mode: TradingModeEnum = TradingModeEnum.ALERT
        self.pending_alerts: dict[str, dict] = {}
        self.trailing_stops: dict[str, float] = {}
        self.risk_settings: RiskSettings = RiskSettings()


_trading_state = TradingState()


def get_trading_state() -> TradingState:
    """Dependency to get trading state."""
    return _trading_state


def get_risk_manager() -> RiskManager:
    """Dependency to get RiskManager instance."""
    return RiskManager()


def _risk_action_to_enum(action: RiskAction) -> RiskActionEnum:
    """Convert RiskAction to RiskActionEnum."""
    mapping = {
        RiskAction.HOLD: RiskActionEnum.HOLD,
        RiskAction.STOP_LOSS: RiskActionEnum.STOP_LOSS,
        RiskAction.TAKE_PROFIT: RiskActionEnum.TAKE_PROFIT,
        RiskAction.TRAILING_STOP: RiskActionEnum.TRAILING_STOP,
    }
    return mapping.get(action, RiskActionEnum.HOLD)


@router.get("/status", response_model=TradingStatusResponse)
def get_trading_status(
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> TradingStatusResponse:
    """
    Get current trading status.

    Returns:
        TradingStatusResponse with mode, pending alerts count, and trailing stops count
    """
    return TradingStatusResponse(
        mode=state.mode,
        pending_alerts_count=len(state.pending_alerts),
        trailing_stops_count=len(state.trailing_stops),
    )


@router.post("/mode", response_model=TradingStatusResponse)
def set_trading_mode(
    request: SetModeRequest,
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> TradingStatusResponse:
    """
    Set trading mode (AUTO or ALERT).

    Args:
        request: SetModeRequest with new mode
        state: Trading state

    Returns:
        TradingStatusResponse with updated status
    """
    state.mode = request.mode
    return TradingStatusResponse(
        mode=state.mode,
        pending_alerts_count=len(state.pending_alerts),
        trailing_stops_count=len(state.trailing_stops),
    )


@router.get("/alerts", response_model=AlertListResponse)
def get_pending_alerts(
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> AlertListResponse:
    """
    Get all pending alerts.

    Returns:
        AlertListResponse with list of pending alerts
    """
    alerts = []
    for alert_id, alert_data in state.pending_alerts.items():
        alerts.append(
            AlertSchema(
                alert_id=alert_id,
                stock_code=alert_data.get("stock_code", ""),
                signal_type=SignalTypeEnum(alert_data.get("signal_type", "HOLD")),
                confidence=alert_data.get("confidence", 0.0),
                reason=alert_data.get("reason", ""),
                current_price=alert_data.get("current_price", 0.0),
                suggested_quantity=alert_data.get("suggested_quantity", 0),
                created_at=alert_data.get("created_at", datetime.now()),
            )
        )
    return AlertListResponse(alerts=alerts)


@router.post("/alerts/approve", response_model=OrderResponse)
async def approve_alert(
    request: ApproveAlertRequest,
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> OrderResponse:
    """
    Approve a pending alert and execute the order.

    Args:
        request: ApproveAlertRequest with alert_id
        state: Trading state

    Returns:
        OrderResponse with execution result

    Raises:
        HTTPException: If alert not found
    """
    if request.alert_id not in state.pending_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = state.pending_alerts.pop(request.alert_id)

    # In production, this would execute the actual order via KIS API
    # For now, return a mock success response
    return OrderResponse(
        success=True,
        order_id=f"ORD-{request.alert_id[:8]}",
        message=f"Order executed for {alert.get('stock_code', 'unknown')}",
        status=OrderStatusEnum.PENDING,
    )


@router.post("/alerts/reject")
def reject_alert(
    request: RejectAlertRequest,
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> dict[str, bool]:
    """
    Reject a pending alert.

    Args:
        request: RejectAlertRequest with alert_id
        state: Trading state

    Returns:
        Dict with rejection status

    Raises:
        HTTPException: If alert not found
    """
    if request.alert_id not in state.pending_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    state.pending_alerts.pop(request.alert_id)
    return {"rejected": True}


@router.post("/risk/check", response_model=RiskCheckResponse)
def check_position_risk(
    request: RiskCheckRequest,
    risk_manager: Annotated[RiskManager, Depends(get_risk_manager)],
) -> RiskCheckResponse:
    """
    Check position for risk triggers (stop-loss, take-profit, trailing stop).

    Args:
        request: RiskCheckRequest with entry and current prices
        risk_manager: RiskManager instance

    Returns:
        RiskCheckResponse with recommended action
    """
    result = risk_manager.check_position(
        entry_price=request.entry_price,
        current_price=request.current_price,
        trailing_stop=None,  # Would be provided from position data
    )

    return RiskCheckResponse(
        action=_risk_action_to_enum(result.action),
        reason=result.reason,
        current_profit_pct=result.current_profit_pct,
        trigger_price=result.trigger_price,
    )


@router.post("/risk/position-size", response_model=PositionSizeResponse)
def calculate_position_size(
    request: PositionSizeRequest,
    risk_manager: Annotated[RiskManager, Depends(get_risk_manager)],
) -> PositionSizeResponse:
    """
    Calculate recommended position size based on risk management rules.

    Args:
        request: PositionSizeRequest with capital and price info
        risk_manager: RiskManager instance

    Returns:
        PositionSizeResponse with recommended quantity
    """
    quantity = risk_manager.calculate_position_size(
        available_capital=request.available_capital,
        stock_price=request.stock_price,
        risk_per_trade_pct=request.risk_per_trade_pct,
    )

    return PositionSizeResponse(quantity=quantity)


@router.post("/risk/can-open", response_model=CanOpenPositionResponse)
def check_can_open_position(
    request: CanOpenPositionRequest,
    risk_manager: Annotated[RiskManager, Depends(get_risk_manager)],
) -> CanOpenPositionResponse:
    """
    Check if a new position can be opened based on risk limits.

    Args:
        request: CanOpenPositionRequest with investment details
        risk_manager: RiskManager instance

    Returns:
        CanOpenPositionResponse indicating if position can be opened
    """
    can_open, reason = risk_manager.can_open_position(
        investment_amount=request.investment_amount,
        current_positions_count=request.current_positions_count,
        daily_pnl_pct=request.daily_pnl_pct,
    )

    return CanOpenPositionResponse(can_open=can_open, reason=reason)


@router.get("/risk-settings", response_model=RiskSettingsResponse)
def get_risk_settings(
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> RiskSettingsResponse:
    """
    Get current risk settings.

    Returns:
        RiskSettingsResponse with stop-loss, take-profit, and daily loss limit
    """
    return RiskSettingsResponse(
        stop_loss_pct=state.risk_settings.stop_loss_pct,
        take_profit_pct=state.risk_settings.take_profit_pct,
        daily_loss_limit_pct=state.risk_settings.daily_loss_limit_pct,
    )


@router.post("/risk-settings", response_model=RiskSettingsResponse)
def update_risk_settings(
    request: RiskSettingsRequest,
    state: Annotated[TradingState, Depends(get_trading_state)],
) -> RiskSettingsResponse:
    """
    Update risk settings.

    Args:
        request: RiskSettingsRequest with new settings
        state: Trading state

    Returns:
        RiskSettingsResponse with updated settings
    """
    state.risk_settings.stop_loss_pct = request.stop_loss_pct
    state.risk_settings.take_profit_pct = request.take_profit_pct
    state.risk_settings.daily_loss_limit_pct = request.daily_loss_limit_pct

    return RiskSettingsResponse(
        stop_loss_pct=state.risk_settings.stop_loss_pct,
        take_profit_pct=state.risk_settings.take_profit_pct,
        daily_loss_limit_pct=state.risk_settings.daily_loss_limit_pct,
    )


@router.get("/targets", response_model=TradingTargetsResponse)
async def get_trading_targets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TradingTargetsResponse:
    """
    Get active watchlist stock codes for trading.

    Returns:
        TradingTargetsResponse with list of stock codes and total count
    """
    service = WatchlistService(db)
    stock_codes = await service.get_active_stock_codes(current_user.id)
    return TradingTargetsResponse(stock_codes=stock_codes, total=len(stock_codes))


@router.get("/settings/{stock_code}", response_model=TradingSettingsResponse | None)
async def get_trading_settings_for_stock(
    stock_code: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TradingSettingsResponse | None:
    """
    Get watchlist trading settings for a specific stock.

    Args:
        stock_code: The stock code to get settings for

    Returns:
        TradingSettingsResponse with target_price, stop_loss_price, quantity
        or None if stock is not in watchlist or not active
    """
    service = WatchlistService(db)
    settings = await service.get_trading_settings(current_user.id, stock_code)
    if not settings:
        return None
    return TradingSettingsResponse(**settings)
