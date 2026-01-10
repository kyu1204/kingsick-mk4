"""
Watchlist service for KingSick.

Provides CRUD operations for user watchlist items.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WatchlistItem


class WatchlistError(Exception):
    """Raised when watchlist operation fails."""

    pass


class WatchlistService:
    """Service for managing user watchlist items."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the watchlist service.

        Args:
            db: The database session.
        """
        self.db = db

    async def create_item(
        self,
        user_id: uuid.UUID,
        stock_code: str,
        stock_name: str,
        target_price: Decimal | None = None,
        stop_loss_price: Decimal | None = None,
        quantity: int | None = None,
        memo: str | None = None,
    ) -> WatchlistItem:
        """
        Create a new watchlist item.

        Args:
            user_id: The user's UUID.
            stock_code: Stock code (6 digits).
            stock_name: Stock name.
            target_price: Target price for take profit.
            stop_loss_price: Stop loss price.
            quantity: Trading quantity.
            memo: Optional memo.

        Returns:
            WatchlistItem: The created item.

        Raises:
            WatchlistError: If the stock already exists in user's watchlist.
        """
        # Check if stock already exists
        existing = await self.get_item_by_stock_code(user_id, stock_code)
        if existing:
            raise WatchlistError(f"Stock {stock_code} already in watchlist")

        # Validate stock code format
        if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
            raise WatchlistError("Invalid stock code format (must be 6 digits)")

        # Validate prices
        if target_price is not None and target_price <= 0:
            raise WatchlistError("Target price must be positive")
        if stop_loss_price is not None and stop_loss_price <= 0:
            raise WatchlistError("Stop loss price must be positive")
        if quantity is not None and quantity <= 0:
            raise WatchlistError("Quantity must be positive")

        item = WatchlistItem(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock_name,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            quantity=quantity,
            memo=memo,
            is_active=True,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get_item_by_id(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> WatchlistItem | None:
        """
        Get a watchlist item by ID.

        Args:
            item_id: The item's UUID.
            user_id: Optional user ID to verify ownership.

        Returns:
            WatchlistItem or None: The item if found.
        """
        query = select(WatchlistItem).where(WatchlistItem.id == item_id)
        if user_id:
            query = query.where(WatchlistItem.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_item_by_stock_code(
        self,
        user_id: uuid.UUID,
        stock_code: str,
    ) -> WatchlistItem | None:
        """
        Get a watchlist item by stock code.

        Args:
            user_id: The user's UUID.
            stock_code: The stock code.

        Returns:
            WatchlistItem or None: The item if found.
        """
        result = await self.db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.stock_code == stock_code,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_items(
        self,
        user_id: uuid.UUID,
        active_only: bool = False,
    ) -> list[WatchlistItem]:
        """
        Get all watchlist items for a user.

        Args:
            user_id: The user's UUID.
            active_only: If True, only return active items.

        Returns:
            list[WatchlistItem]: The user's watchlist items.
        """
        query = select(WatchlistItem).where(WatchlistItem.user_id == user_id)
        if active_only:
            query = query.where(WatchlistItem.is_active == True)  # noqa: E712
        query = query.order_by(WatchlistItem.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_items(self, user_id: uuid.UUID) -> list[WatchlistItem]:
        """
        Get all active watchlist items for a user.

        This method is used by the trading engine to get trading targets.

        Args:
            user_id: The user's UUID.

        Returns:
            list[WatchlistItem]: Active watchlist items.
        """
        return await self.get_user_items(user_id, active_only=True)

    async def update_item(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        target_price: Decimal | None = None,
        stop_loss_price: Decimal | None = None,
        quantity: int | None = None,
        memo: str | None = None,
        is_active: bool | None = None,
        clear_target_price: bool = False,
        clear_stop_loss_price: bool = False,
        clear_quantity: bool = False,
        clear_memo: bool = False,
    ) -> WatchlistItem:
        """
        Update a watchlist item.

        Args:
            item_id: The item's UUID.
            user_id: The user's UUID for ownership verification.
            target_price: New target price.
            stop_loss_price: New stop loss price.
            quantity: New quantity.
            memo: New memo.
            is_active: New active status.
            clear_*: Set to True to clear the corresponding field to None.

        Returns:
            WatchlistItem: The updated item.

        Raises:
            WatchlistError: If the item is not found or doesn't belong to user.
        """
        item = await self.get_item_by_id(item_id, user_id)
        if not item:
            raise WatchlistError("Watchlist item not found")

        # Validate prices
        if target_price is not None and target_price <= 0:
            raise WatchlistError("Target price must be positive")
        if stop_loss_price is not None and stop_loss_price <= 0:
            raise WatchlistError("Stop loss price must be positive")
        if quantity is not None and quantity <= 0:
            raise WatchlistError("Quantity must be positive")

        # Update fields
        if clear_target_price:
            item.target_price = None
        elif target_price is not None:
            item.target_price = target_price

        if clear_stop_loss_price:
            item.stop_loss_price = None
        elif stop_loss_price is not None:
            item.stop_loss_price = stop_loss_price

        if clear_quantity:
            item.quantity = None
        elif quantity is not None:
            item.quantity = quantity

        if clear_memo:
            item.memo = None
        elif memo is not None:
            item.memo = memo

        if is_active is not None:
            item.is_active = is_active

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def toggle_active(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WatchlistItem:
        """
        Toggle the active status of a watchlist item.

        Args:
            item_id: The item's UUID.
            user_id: The user's UUID for ownership verification.

        Returns:
            WatchlistItem: The updated item.

        Raises:
            WatchlistError: If the item is not found or doesn't belong to user.
        """
        item = await self.get_item_by_id(item_id, user_id)
        if not item:
            raise WatchlistError("Watchlist item not found")

        item.is_active = not item.is_active
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete_item(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        Delete a watchlist item.

        Args:
            item_id: The item's UUID.
            user_id: The user's UUID for ownership verification.

        Returns:
            bool: True if deleted successfully.

        Raises:
            WatchlistError: If the item is not found or doesn't belong to user.
        """
        item = await self.get_item_by_id(item_id, user_id)
        if not item:
            raise WatchlistError("Watchlist item not found")

        await self.db.delete(item)
        await self.db.flush()
        return True

    async def count_user_items(self, user_id: uuid.UUID) -> int:
        """
        Count the number of items in a user's watchlist.

        Args:
            user_id: The user's UUID.

        Returns:
            int: The number of items.
        """
        items = await self.get_user_items(user_id)
        return len(items)

    async def get_active_stock_codes(self, user_id: uuid.UUID) -> list[str]:
        """
        Get stock codes of active watchlist items.

        This method is used by the trading engine to get trading target codes.

        Args:
            user_id: The user's UUID.

        Returns:
            list[str]: List of stock codes.
        """
        items = await self.get_active_items(user_id)
        return [item.stock_code for item in items]

    async def get_trading_settings(
        self,
        user_id: uuid.UUID,
        stock_code: str,
    ) -> dict | None:
        """
        Get trading settings for a specific stock from watchlist.

        Used by the trading engine to apply watchlist-specific settings.

        Args:
            user_id: The user's UUID.
            stock_code: The stock code.

        Returns:
            dict or None: Trading settings if stock is in watchlist, None otherwise.
                Contains: target_price, stop_loss_price, quantity (all optional).
        """
        item = await self.get_item_by_stock_code(user_id, stock_code)
        if not item or not item.is_active:
            return None

        return {
            "target_price": float(item.target_price) if item.target_price else None,
            "stop_loss_price": float(item.stop_loss_price) if item.stop_loss_price else None,
            "quantity": item.quantity,
        }
