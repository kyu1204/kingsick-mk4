"""
Unit tests for WatchlistService.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import WatchlistItem
from app.services.watchlist import WatchlistError, WatchlistService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create WatchlistService with mock db."""
    return WatchlistService(mock_db)


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def mock_item(user_id):
    """Create a mock watchlist item."""
    item = MagicMock(spec=WatchlistItem)
    item.id = uuid.uuid4()
    item.user_id = user_id
    item.stock_code = "005930"
    item.stock_name = "삼성전자"
    item.target_price = Decimal("80000")
    item.stop_loss_price = Decimal("70000")
    item.quantity = 10
    item.memo = "Test memo"
    item.is_active = True
    return item


class TestCreateItem:
    """Tests for WatchlistService.create_item."""

    async def test_create_item_success(self, service, mock_db, user_id):
        """Create item should add to database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await service.create_item(
            user_id=user_id,
            stock_code="005930",
            stock_name="삼성전자",
            target_price=Decimal("80000"),
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_create_item_duplicate_raises_error(self, service, mock_db, user_id, mock_item):
        """Creating duplicate item should raise WatchlistError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        with pytest.raises(WatchlistError, match="already in watchlist"):
            await service.create_item(
                user_id=user_id,
                stock_code="005930",
                stock_name="삼성전자",
            )

    async def test_create_item_invalid_stock_code(self, service, mock_db, user_id):
        """Invalid stock code should raise WatchlistError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(WatchlistError, match="Invalid stock code format"):
            await service.create_item(
                user_id=user_id,
                stock_code="invalid",
                stock_name="Test",
            )

    async def test_create_item_negative_target_price(self, service, mock_db, user_id):
        """Negative target price should raise WatchlistError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(WatchlistError, match="Target price must be positive"):
            await service.create_item(
                user_id=user_id,
                stock_code="005930",
                stock_name="삼성전자",
                target_price=Decimal("-100"),
            )


class TestGetItemById:
    """Tests for WatchlistService.get_item_by_id."""

    async def test_get_item_by_id_found(self, service, mock_db, mock_item):
        """Get item by ID should return item when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.get_item_by_id(mock_item.id)

        assert result == mock_item

    async def test_get_item_by_id_not_found(self, service, mock_db):
        """Get item by ID should return None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_item_by_id(uuid.uuid4())

        assert result is None


class TestUpdateItem:
    """Tests for WatchlistService.update_item."""

    async def test_update_item_success(self, service, mock_db, mock_item, user_id):
        """Update item should modify fields."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        await service.update_item(
            item_id=mock_item.id,
            user_id=user_id,
            target_price=Decimal("85000"),
        )

        assert mock_item.target_price == Decimal("85000")
        mock_db.flush.assert_called_once()

    async def test_update_item_not_found(self, service, mock_db, user_id):
        """Update non-existent item should raise WatchlistError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(WatchlistError, match="not found"):
            await service.update_item(
                item_id=uuid.uuid4(),
                user_id=user_id,
                target_price=Decimal("85000"),
            )

    async def test_update_item_clear_field(self, service, mock_db, mock_item, user_id):
        """Update with clear flag should set field to None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        await service.update_item(
            item_id=mock_item.id,
            user_id=user_id,
            clear_target_price=True,
        )

        assert mock_item.target_price is None


class TestToggleActive:
    """Tests for WatchlistService.toggle_active."""

    async def test_toggle_active_success(self, service, mock_db, mock_item, user_id):
        """Toggle should flip is_active status."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result
        original_status = mock_item.is_active

        await service.toggle_active(mock_item.id, user_id)

        assert mock_item.is_active != original_status


class TestDeleteItem:
    """Tests for WatchlistService.delete_item."""

    async def test_delete_item_success(self, service, mock_db, mock_item, user_id):
        """Delete item should remove from database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.delete_item(mock_item.id, user_id)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_item)


class TestGetActiveStockCodes:
    """Tests for WatchlistService.get_active_stock_codes."""

    async def test_get_active_stock_codes_success(self, service, mock_db, user_id):
        """Should return list of active stock codes."""
        mock_items = []
        for code in ["005930", "000660", "035420"]:
            item = MagicMock(spec=WatchlistItem)
            item.stock_code = code
            item.is_active = True
            mock_items.append(item)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_items
        mock_db.execute.return_value = mock_result

        result = await service.get_active_stock_codes(user_id)

        assert result == ["005930", "000660", "035420"]

    async def test_get_active_stock_codes_empty(self, service, mock_db, user_id):
        """Should return empty list when no active items."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_active_stock_codes(user_id)

        assert result == []


class TestGetTradingSettings:
    """Tests for WatchlistService.get_trading_settings."""

    async def test_get_trading_settings_found(self, service, mock_db, user_id, mock_item):
        """Should return trading settings for active stock."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.get_trading_settings(user_id, "005930")

        assert result is not None
        assert result["target_price"] == 80000.0
        assert result["stop_loss_price"] == 70000.0
        assert result["quantity"] == 10

    async def test_get_trading_settings_not_found(self, service, mock_db, user_id):
        """Should return None for non-existent stock."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_trading_settings(user_id, "999999")

        assert result is None

    async def test_get_trading_settings_inactive(self, service, mock_db, user_id, mock_item):
        """Should return None for inactive stock."""
        mock_item.is_active = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.get_trading_settings(user_id, "005930")

        assert result is None

    async def test_get_trading_settings_with_null_fields(self, service, mock_db, user_id):
        """Should handle null optional fields."""
        mock_item = MagicMock(spec=WatchlistItem)
        mock_item.is_active = True
        mock_item.target_price = None
        mock_item.stop_loss_price = None
        mock_item.quantity = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.get_trading_settings(user_id, "005930")

        assert result is not None
        assert result["target_price"] is None
        assert result["stop_loss_price"] is None
        assert result["quantity"] is None
