"""
Watchlist model for KingSick trading system.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WatchlistItem(Base):
    """
    Watchlist item model.

    Stores user's watchlist stocks with individual trading settings.
    Each user can have multiple stocks, but no duplicates.
    """

    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )
    stock_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Trading settings (nullable - use defaults if not set)
    target_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    stop_loss_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    memo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="watchlist_items",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "stock_code", name="uq_user_stock"),
        CheckConstraint("target_price IS NULL OR target_price > 0", name="chk_target_price"),
        CheckConstraint("stop_loss_price IS NULL OR stop_loss_price > 0", name="chk_stop_loss_price"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="chk_quantity"),
    )

    def __repr__(self) -> str:
        return f"<WatchlistItem {self.stock_code} ({self.stock_name})>"
