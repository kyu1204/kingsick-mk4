"""
User model for KingSick authentication system.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """
    User account model.

    Stores user credentials and profile information.
    Admin users can create invitation links.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    # Telegram integration fields
    telegram_chat_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    telegram_linked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    api_key: Mapped["UserApiKey | None"] = relationship(
        "UserApiKey",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    created_invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="created_by_user",
        foreign_keys="Invitation.created_by",
        cascade="all, delete-orphan",
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(  # noqa: F821
        "WatchlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    telegram_link_tokens: Mapped[list["TelegramLinkToken"]] = relationship(  # noqa: F821
        "TelegramLinkToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Invitation(Base):
    """
    Invitation link model.

    Admin users create invitations that allow new users to register.
    Each invitation can only be used once.
    """

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="created_invitations",
        foreign_keys=[created_by],
    )

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still valid (not used and not expired)."""
        if self.used_at is not None:
            return False
        return datetime.now(self.expires_at.tzinfo) < self.expires_at

    def __repr__(self) -> str:
        return f"<Invitation {self.code[:8]}...>"


class UserApiKey(Base):
    """
    User API key model for KIS (Korea Investment & Securities) API.

    Stores encrypted API credentials for each user.
    Each user can have only one set of API keys.
    """

    __tablename__ = "user_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    kis_app_key_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    kis_app_secret_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    kis_account_no_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    is_paper_trading: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_key",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<UserApiKey user_id={self.user_id}>"
