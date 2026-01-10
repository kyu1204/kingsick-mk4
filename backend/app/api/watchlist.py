"""
Watchlist API router for KingSick.

Provides endpoints for managing user watchlist items.
"""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.watchlist import WatchlistError, WatchlistService

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


# Request/Response schemas


class WatchlistItemCreate(BaseModel):
    """Request body for creating a watchlist item."""

    stock_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    stock_name: str = Field(..., min_length=1, max_length=100)
    target_price: Decimal | None = Field(None, gt=0)
    stop_loss_price: Decimal | None = Field(None, gt=0)
    quantity: int | None = Field(None, gt=0)
    memo: str | None = Field(None, max_length=500)


class WatchlistItemUpdate(BaseModel):
    """Request body for updating a watchlist item."""

    target_price: Decimal | None = Field(None, gt=0)
    stop_loss_price: Decimal | None = Field(None, gt=0)
    quantity: int | None = Field(None, gt=0)
    memo: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    clear_target_price: bool = False
    clear_stop_loss_price: bool = False
    clear_quantity: bool = False
    clear_memo: bool = False


class WatchlistItemResponse(BaseModel):
    """Response for a single watchlist item."""

    id: str
    stock_code: str
    stock_name: str
    is_active: bool
    target_price: Decimal | None
    stop_loss_price: Decimal | None
    quantity: int | None
    memo: str | None
    created_at: str
    updated_at: str
    # current_price will be added when fetching from KIS API
    current_price: Decimal | None = None
    price_change: float | None = None

    class Config:
        from_attributes = True


class WatchlistListResponse(BaseModel):
    """Response for list of watchlist items."""

    items: list[WatchlistItemResponse]
    total: int


class ToggleResponse(BaseModel):
    """Response for toggle operation."""

    id: str
    is_active: bool


class DeleteResponse(BaseModel):
    """Response for delete operation."""

    message: str = "Item deleted successfully"


# Helper functions


def item_to_response(item) -> WatchlistItemResponse:
    """Convert WatchlistItem model to response schema."""
    return WatchlistItemResponse(
        id=str(item.id),
        stock_code=item.stock_code,
        stock_name=item.stock_name,
        is_active=item.is_active,
        target_price=item.target_price,
        stop_loss_price=item.stop_loss_price,
        quantity=item.quantity,
        memo=item.memo,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
        current_price=None,  # TODO: Fetch from KIS API
        price_change=None,
    )


# Endpoints


@router.post(
    "",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_watchlist_item(
    request: WatchlistItemCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add a new stock to the watchlist.

    Requires authentication.
    """
    try:
        service = WatchlistService(db)
        item = await service.create_item(
            user_id=current_user.id,
            stock_code=request.stock_code,
            stock_name=request.stock_name,
            target_price=request.target_price,
            stop_loss_price=request.stop_loss_price,
            quantity=request.quantity,
            memo=request.memo,
        )
        await db.commit()
        return item_to_response(item)

    except WatchlistError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=WatchlistListResponse,
)
async def get_watchlist(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = False,
):
    """
    Get all watchlist items for the current user.

    Requires authentication.
    """
    service = WatchlistService(db)
    items = await service.get_user_items(current_user.id, active_only=active_only)

    # TODO: Fetch current prices from KIS API for each item

    return WatchlistListResponse(
        items=[item_to_response(item) for item in items],
        total=len(items),
    )


@router.get(
    "/{item_id}",
    response_model=WatchlistItemResponse,
)
async def get_watchlist_item(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a single watchlist item by ID.

    Requires authentication.
    """
    service = WatchlistService(db)
    item = await service.get_item_by_id(item_id, current_user.id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )

    return item_to_response(item)


@router.put(
    "/{item_id}",
    response_model=WatchlistItemResponse,
)
async def update_watchlist_item(
    item_id: UUID,
    request: WatchlistItemUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a watchlist item.

    Requires authentication.
    """
    try:
        service = WatchlistService(db)
        item = await service.update_item(
            item_id=item_id,
            user_id=current_user.id,
            target_price=request.target_price,
            stop_loss_price=request.stop_loss_price,
            quantity=request.quantity,
            memo=request.memo,
            is_active=request.is_active,
            clear_target_price=request.clear_target_price,
            clear_stop_loss_price=request.clear_stop_loss_price,
            clear_quantity=request.clear_quantity,
            clear_memo=request.clear_memo,
        )
        await db.commit()
        return item_to_response(item)

    except WatchlistError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch(
    "/{item_id}/toggle",
    response_model=ToggleResponse,
)
async def toggle_watchlist_item(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Toggle the active status of a watchlist item.

    Requires authentication.
    """
    try:
        service = WatchlistService(db)
        item = await service.toggle_active(item_id, current_user.id)
        await db.commit()
        return ToggleResponse(id=str(item.id), is_active=item.is_active)

    except WatchlistError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete(
    "/{item_id}",
    response_model=DeleteResponse,
)
async def delete_watchlist_item(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a watchlist item.

    Requires authentication.
    """
    try:
        service = WatchlistService(db)
        await service.delete_item(item_id, current_user.id)
        await db.commit()
        return DeleteResponse()

    except WatchlistError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
