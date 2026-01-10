"""
Telegram API router for bot webhook and user linking.

Provides endpoints for:
- Creating Telegram link tokens (Deep Link)
- Checking link status
- Unlinking Telegram account
- Webhook for Telegram updates
"""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.telegram_link import TelegramLinkToken
from app.models.user import User
from app.services.telegram_service import get_telegram_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["Telegram"])


# Request/Response schemas


class LinkResponse(BaseModel):
    """Response with Deep Link URL."""

    deep_link: str
    expires_in: int  # seconds


class StatusResponse(BaseModel):
    """Response with Telegram link status."""

    linked: bool
    linked_at: datetime | None = None


class UnlinkResponse(BaseModel):
    """Response for successful unlink."""

    message: str = "Telegram 연동이 해제되었습니다"


class WebhookResponse(BaseModel):
    """Response for webhook processing."""

    ok: bool = True


# Helper functions


async def get_or_create_link_token(
    db: AsyncSession,
    user_id: str,
) -> TelegramLinkToken:
    """
    Get existing valid token or create a new one.

    Invalidates any existing unused tokens for the user.
    """
    import uuid

    user_uuid = uuid.UUID(user_id)

    # Invalidate existing unused tokens
    result = await db.execute(
        select(TelegramLinkToken).where(
            TelegramLinkToken.user_id == user_uuid,
            TelegramLinkToken.used == False,  # noqa: E712
        )
    )
    existing_tokens = result.scalars().all()
    for token in existing_tokens:
        token.used = True

    # Create new token
    new_token = TelegramLinkToken.create_token(user_uuid)
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)

    return new_token


async def validate_and_use_token(
    db: AsyncSession,
    token_str: str,
) -> TelegramLinkToken | None:
    """
    Validate a link token and mark it as used.

    Returns the token if valid, None otherwise.
    """
    result = await db.execute(
        select(TelegramLinkToken).where(
            TelegramLinkToken.token == token_str,
        )
    )
    token = result.scalar_one_or_none()

    if token is None:
        return None

    if not token.is_valid:
        return None

    # Mark as used
    token.used = True
    await db.commit()

    return token


async def link_user_telegram(
    db: AsyncSession,
    user_id: str,
    chat_id: str,
) -> User:
    """Link a user's account to their Telegram chat ID."""
    import uuid

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    user.telegram_chat_id = chat_id
    user.telegram_linked_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)

    return user


async def unlink_user_telegram(
    db: AsyncSession,
    user_id: str,
) -> User:
    """Unlink a user's Telegram account."""
    import uuid

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found")

    user.telegram_chat_id = None
    user.telegram_linked_at = None
    await db.commit()
    await db.refresh(user)

    return user


async def get_user_by_chat_id(
    db: AsyncSession,
    chat_id: str,
) -> User | None:
    """Get a user by their Telegram chat ID."""
    result = await db.execute(
        select(User).where(User.telegram_chat_id == chat_id)
    )
    return result.scalar_one_or_none()


# Endpoints


@router.post("/link", response_model=LinkResponse)
async def create_link_token(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LinkResponse:
    """
    Create a Telegram link token.

    Returns a Deep Link URL that the user can click to link their Telegram account.
    The link expires in 10 minutes.
    """
    telegram_service = get_telegram_service()

    if not telegram_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram integration is not enabled",
        )

    token = await get_or_create_link_token(db, str(current_user.id))
    deep_link = telegram_service.get_deep_link_url(token.token)

    # Calculate expires_in in seconds
    now = datetime.now(UTC)
    expires_at = token.expires_at.replace(tzinfo=UTC)
    expires_in = int((expires_at - now).total_seconds())

    return LinkResponse(
        deep_link=deep_link,
        expires_in=max(0, expires_in),
    )


@router.get("/status", response_model=StatusResponse)
async def get_link_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> StatusResponse:
    """
    Get the current Telegram link status.

    Returns whether the user's account is linked to Telegram.
    """
    return StatusResponse(
        linked=current_user.telegram_chat_id is not None,
        linked_at=current_user.telegram_linked_at,
    )


@router.delete("/link", response_model=UnlinkResponse)
async def unlink_telegram(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnlinkResponse:
    """
    Unlink the user's Telegram account.

    After unlinking, the user will no longer receive alerts via Telegram.
    """
    if current_user.telegram_chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account is not linked",
        )

    await unlink_user_telegram(db, str(current_user.id))
    return UnlinkResponse()


@router.post("/webhook", response_model=WebhookResponse)
async def telegram_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> WebhookResponse:
    """
    Handle Telegram webhook updates.

    This endpoint receives updates from Telegram when users interact with the bot.
    Handles:
    - /start command with Deep Link token for account linking
    - Callback queries for alert approval/rejection
    """
    settings = get_settings()
    telegram_service = get_telegram_service()

    # Verify secret token
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            logger.warning("Invalid webhook secret token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid secret token",
            )

    try:
        update_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    logger.debug(f"Received Telegram update: {update_data}")

    # Handle /start command (Deep Link)
    if "message" in update_data:
        message = update_data["message"]
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", ""))

        if text.startswith("/start "):
            # Extract token from /start command
            token_str = text[7:].strip()  # Remove "/start " prefix

            token = await validate_and_use_token(db, token_str)
            if token is None:
                await telegram_service.send_error_message(
                    chat_id,
                    "링크가 만료되었거나 이미 사용되었습니다.\n새 링크를 생성해주세요.",
                )
            else:
                # Link the user
                await link_user_telegram(db, str(token.user_id), chat_id)
                await telegram_service.send_link_success_message(chat_id)

        elif text == "/start":
            await telegram_service.send_error_message(
                chat_id,
                "올바른 연동 링크를 사용해주세요.\nKingSick 앱의 Settings에서 Telegram 연동을 시작하세요.",
            )

    # Handle callback queries (button clicks)
    elif "callback_query" in update_data:
        callback_query = update_data["callback_query"]
        callback_id = callback_query.get("id", "")
        data = callback_query.get("data", "")
        chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id", ""))
        message_id = callback_query.get("message", {}).get("message_id")

        # Verify user is linked
        user = await get_user_by_chat_id(db, chat_id)
        if user is None:
            await telegram_service.answer_callback(
                callback_id,
                "연동된 계정을 찾을 수 없습니다.",
                show_alert=True,
            )
            return WebhookResponse()

        # Parse callback data
        parsed = telegram_service.parse_callback_data(data)
        if parsed is None:
            await telegram_service.answer_callback(
                callback_id,
                "잘못된 요청입니다.",
                show_alert=True,
            )
            return WebhookResponse()

        action, alert_id = parsed

        # Import here to avoid circular import
        from app.services.trading_engine import get_trading_engine

        trading_engine = get_trading_engine()

        if action == "approve":
            try:
                result = trading_engine.approve_alert(alert_id)
                if result:
                    await telegram_service.answer_callback(
                        callback_id,
                        "✅ 주문이 실행되었습니다!",
                    )
                    result_text = (
                        f"📈 종목: {result.get('stock_name', 'N/A')}\n"
                        f"📊 {result.get('action', 'N/A')}: "
                        f"{result.get('quantity', 0)}주"
                    )
                    await telegram_service.edit_message_after_action(
                        chat_id,
                        message_id,
                        "approved",
                        result_text,
                    )
                else:
                    await telegram_service.answer_callback(
                        callback_id,
                        "⚠️ 알림을 찾을 수 없거나 이미 처리되었습니다.",
                        show_alert=True,
                    )
            except Exception as e:
                logger.error(f"Failed to approve alert: {e}")
                await telegram_service.answer_callback(
                    callback_id,
                    f"❌ 주문 실행 실패: {str(e)}",
                    show_alert=True,
                )

        else:  # reject
            try:
                result = trading_engine.reject_alert(alert_id)
                if result:
                    await telegram_service.answer_callback(
                        callback_id,
                        "알림이 거절되었습니다.",
                    )
                    await telegram_service.edit_message_after_action(
                        chat_id,
                        message_id,
                        "rejected",
                        f"📈 종목: {result.get('stock_name', 'N/A')}",
                    )
                else:
                    await telegram_service.answer_callback(
                        callback_id,
                        "⚠️ 알림을 찾을 수 없거나 이미 처리되었습니다.",
                        show_alert=True,
                    )
            except Exception as e:
                logger.error(f"Failed to reject alert: {e}")
                await telegram_service.answer_callback(
                    callback_id,
                    f"❌ 처리 실패: {str(e)}",
                    show_alert=True,
                )

    return WebhookResponse()
