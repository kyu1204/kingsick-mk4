"""
Telegram link token model for Deep Link user authentication.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Token expiry time in minutes
TOKEN_EXPIRY_MINUTES = 10


class TelegramLinkToken(Base):
    """
    Telegram Deep Link token for connecting user accounts.

    Generated when user requests to link their Telegram account.
    Token is embedded in Deep Link: t.me/BotName?start={token}
    Expires after 10 minutes and can only be used once.
    """

    __tablename__ = "telegram_link_tokens"

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
    token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="telegram_link_tokens",
    )

    @classmethod
    def create_token(cls, user_id: uuid.UUID) -> "TelegramLinkToken":
        """
        Create a new token for the given user.

        Args:
            user_id: The user's UUID.

        Returns:
            A new TelegramLinkToken instance.
        """
        now = datetime.now(UTC)
        return cls(
            user_id=user_id,
            token=secrets.token_urlsafe(16)[:24],  # 24 char URL-safe token
            created_at=now,
            expires_at=now + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
            used=False,
        )

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not used and not expired)."""
        if self.used:
            return False
        return datetime.now(UTC) < self.expires_at.replace(tzinfo=UTC)

    def __repr__(self) -> str:
        return f"<TelegramLinkToken {self.token[:8]}... user_id={self.user_id}>"
