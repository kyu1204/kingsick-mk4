"""
Telegram Bot service for sending alerts and handling user interactions.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Alert expiry time in minutes
ALERT_EXPIRY_MINUTES = 5

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds (exponential backoff)


@dataclass
class AlertInfo:
    """Information about a trading alert for Telegram message."""

    alert_id: str
    stock_code: str
    stock_name: str
    signal: str  # "BUY" or "SELL"
    confidence: float
    current_price: float
    target_price: float | None
    stop_loss_price: float | None
    reasoning: list[str]
    created_at: datetime


class TelegramService:
    """
    Service for Telegram Bot operations.

    Handles sending alerts, processing callbacks, and user linking.
    """

    def __init__(self) -> None:
        """Initialize Telegram service."""
        self.settings = get_settings()
        self._bot: Bot | None = None

    @property
    def bot(self) -> Bot:
        """Get or create the Telegram Bot instance."""
        if self._bot is None:
            if not self.settings.telegram_bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
            self._bot = Bot(token=self.settings.telegram_bot_token)
        return self._bot

    @property
    def is_enabled(self) -> bool:
        """Check if Telegram integration is enabled."""
        return (
            self.settings.telegram_enabled
            and bool(self.settings.telegram_bot_token)
        )

    def _format_alert_message(self, alert: AlertInfo) -> str:
        """
        Format an alert into a Telegram message.

        Args:
            alert: The alert information.

        Returns:
            Formatted message string with HTML formatting.
        """
        signal_emoji = "🟢" if alert.signal == "BUY" else "🔴"
        signal_text = "매수" if alert.signal == "BUY" else "매도"

        lines = [
            "🔔 <b>매매 알림</b>",
            "",
            f"📈 종목: {alert.stock_name} ({alert.stock_code})",
            f"📊 신호: {signal_emoji} {signal_text} ({alert.confidence:.0%})",
            f"💰 현재가: {alert.current_price:,.0f}원",
        ]

        if alert.target_price:
            lines.append(f"🎯 목표가: {alert.target_price:,.0f}원")
        if alert.stop_loss_price:
            lines.append(f"🛑 손절가: {alert.stop_loss_price:,.0f}원")

        lines.append("")
        lines.append("<b>판단 근거:</b>")
        for reason in alert.reasoning:
            lines.append(f"• {reason}")

        lines.append("")
        lines.append(f"⏰ {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def _create_alert_keyboard(self, alert_id: str) -> InlineKeyboardMarkup:
        """
        Create inline keyboard for alert approval/rejection.

        Args:
            alert_id: The alert ID to embed in callback data.

        Returns:
            InlineKeyboardMarkup with approve and reject buttons.
        """
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ 승인",
                    callback_data=f"approve:{alert_id}"
                ),
                InlineKeyboardButton(
                    "❌ 거절",
                    callback_data=f"reject:{alert_id}"
                ),
            ]
        ])

    async def send_alert(
        self,
        chat_id: str,
        alert: AlertInfo,
    ) -> dict[str, Any] | None:
        """
        Send a trading alert to a Telegram chat.

        Args:
            chat_id: The Telegram chat ID to send to.
            alert: The alert information.

        Returns:
            Message info dict if successful, None if failed.
        """
        if not self.is_enabled:
            logger.warning("Telegram is not enabled, skipping alert")
            return None

        message_text = self._format_alert_message(alert)
        keyboard = self._create_alert_keyboard(alert.alert_id)

        for attempt in range(MAX_RETRIES):
            try:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                logger.info(
                    f"Alert sent to chat_id={chat_id}, "
                    f"message_id={message.message_id}"
                )
                return {
                    "message_id": message.message_id,
                    "chat_id": chat_id,
                    "alert_id": alert.alert_id,
                }
            except TelegramError as e:
                logger.error(
                    f"Failed to send alert (attempt {attempt + 1}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                else:
                    raise

        return None

    async def answer_callback(
        self,
        callback_query_id: str,
        text: str,
        show_alert: bool = False,
    ) -> bool:
        """
        Answer a callback query from an inline button click.

        Args:
            callback_query_id: The callback query ID.
            text: Text to show to the user.
            show_alert: Whether to show as an alert popup.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_enabled:
            return False

        try:
            await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert,
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to answer callback: {e}")
            return False

    async def edit_message_after_action(
        self,
        chat_id: str,
        message_id: int,
        action: str,
        result_text: str,
    ) -> bool:
        """
        Edit a message after user takes action (approve/reject).

        Removes the inline keyboard and updates the message.

        Args:
            chat_id: The Telegram chat ID.
            message_id: The message ID to edit.
            action: The action taken ("approved" or "rejected").
            result_text: Additional result text to show.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_enabled:
            return False

        if action == "approved":
            new_text = f"✅ <b>주문 실행 완료</b>\n\n{result_text}"
        else:
            new_text = f"❌ <b>알림 거절됨</b>\n\n{result_text}"

        new_text += f"\n\n⏰ {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text,
                parse_mode="HTML",
                reply_markup=None,  # Remove keyboard
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to edit message: {e}")
            return False

    async def send_link_success_message(self, chat_id: str) -> bool:
        """
        Send a success message after user links their account.

        Args:
            chat_id: The Telegram chat ID.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_enabled:
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ <b>KingSick 연동 완료!</b>\n\n"
                    "이제 매매 알림을 Telegram으로 받을 수 있습니다.\n"
                    "알림에서 승인/거절 버튼을 눌러 주문을 실행하세요."
                ),
                parse_mode="HTML",
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send link success message: {e}")
            return False

    async def send_error_message(self, chat_id: str, error_text: str) -> bool:
        """
        Send an error message to a user.

        Args:
            chat_id: The Telegram chat ID.
            error_text: The error message to send.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_enabled:
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {error_text}",
                parse_mode="HTML",
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send error message: {e}")
            return False

    def parse_callback_data(self, data: str) -> tuple[str, str] | None:
        """
        Parse callback data from an inline button click.

        Args:
            data: The callback_data string (e.g., "approve:alert_id").

        Returns:
            Tuple of (action, alert_id) or None if invalid.
        """
        if ":" not in data:
            return None

        parts = data.split(":", 1)
        if len(parts) != 2:
            return None

        action, alert_id = parts
        if action not in ("approve", "reject"):
            return None

        return action, alert_id

    def get_deep_link_url(self, token: str) -> str:
        """
        Generate a Deep Link URL for user account linking.

        Args:
            token: The linking token.

        Returns:
            The full Deep Link URL.
        """
        bot_username = self.settings.telegram_bot_username
        if not bot_username:
            raise ValueError("TELEGRAM_BOT_USERNAME is not configured")
        return f"https://t.me/{bot_username}?start={token}"


# Singleton instance
_telegram_service: TelegramService | None = None


def get_telegram_service() -> TelegramService:
    """Get the singleton TelegramService instance."""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service
