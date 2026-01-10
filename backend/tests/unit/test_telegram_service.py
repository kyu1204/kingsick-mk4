"""
Unit tests for TelegramService.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.telegram_service import (
    AlertInfo,
    TelegramService,
    get_telegram_service,
)


class TestAlertInfo:
    """Tests for AlertInfo dataclass."""

    def test_create_alert_info(self):
        """AlertInfo should be created with all required fields."""
        alert = AlertInfo(
            alert_id="alert-123",
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.85,
            current_price=72500.0,
            target_price=79000.0,
            stop_loss_price=68000.0,
            reasoning=["RSI < 30", "Volume spike"],
            created_at=datetime.now(UTC),
        )
        assert alert.alert_id == "alert-123"
        assert alert.stock_code == "005930"
        assert alert.stock_name == "삼성전자"
        assert alert.signal == "BUY"
        assert alert.confidence == 0.85
        assert alert.current_price == 72500.0

    def test_alert_info_with_none_prices(self):
        """AlertInfo should allow None for optional price fields."""
        alert = AlertInfo(
            alert_id="alert-456",
            stock_code="000660",
            stock_name="SK하이닉스",
            signal="SELL",
            confidence=0.72,
            current_price=145000.0,
            target_price=None,
            stop_loss_price=None,
            reasoning=["RSI > 70"],
            created_at=datetime.now(UTC),
        )
        assert alert.target_price is None
        assert alert.stop_loss_price is None


class TestTelegramService:
    """Tests for TelegramService class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for tests."""
        settings = MagicMock()
        settings.telegram_enabled = True
        settings.telegram_bot_token = "test-bot-token"
        settings.telegram_bot_username = "test_bot"
        return settings

    @pytest.fixture
    def telegram_service(self, mock_settings):
        """Create TelegramService with mocked settings."""
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings
            return service

    def test_is_enabled_when_configured(self, telegram_service):
        """is_enabled should return True when properly configured."""
        assert telegram_service.is_enabled is True

    def test_is_enabled_when_disabled(self, mock_settings):
        """is_enabled should return False when telegram_enabled is False."""
        mock_settings.telegram_enabled = False
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings
            assert service.is_enabled is False

    def test_is_enabled_without_token(self, mock_settings):
        """is_enabled should return False when token is missing."""
        mock_settings.telegram_bot_token = ""
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings
            assert service.is_enabled is False

    def test_format_alert_message_buy(self, telegram_service):
        """_format_alert_message should format BUY alert correctly."""
        alert = AlertInfo(
            alert_id="alert-123",
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.85,
            current_price=72500.0,
            target_price=79000.0,
            stop_loss_price=68000.0,
            reasoning=["RSI < 30", "Volume spike"],
            created_at=datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC),
        )
        message = telegram_service._format_alert_message(alert)

        assert "🔔 <b>매매 알림</b>" in message
        assert "삼성전자 (005930)" in message
        assert "🟢" in message  # BUY emoji
        assert "매수" in message
        assert "85%" in message
        assert "72,500원" in message
        assert "79,000원" in message
        assert "68,000원" in message
        assert "RSI < 30" in message
        assert "Volume spike" in message

    def test_format_alert_message_sell(self, telegram_service):
        """_format_alert_message should format SELL alert correctly."""
        alert = AlertInfo(
            alert_id="alert-456",
            stock_code="000660",
            stock_name="SK하이닉스",
            signal="SELL",
            confidence=0.72,
            current_price=145000.0,
            target_price=None,
            stop_loss_price=None,
            reasoning=["RSI > 70"],
            created_at=datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC),
        )
        message = telegram_service._format_alert_message(alert)

        assert "🔴" in message  # SELL emoji
        assert "매도" in message
        assert "72%" in message
        assert "145,000원" in message
        assert "🎯 목표가" not in message  # No target price
        assert "🛑 손절가" not in message  # No stop loss

    def test_create_alert_keyboard(self, telegram_service):
        """_create_alert_keyboard should create approve/reject buttons."""
        keyboard = telegram_service._create_alert_keyboard("alert-123")

        # Check structure
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

        # Check buttons
        approve_btn = keyboard.inline_keyboard[0][0]
        reject_btn = keyboard.inline_keyboard[0][1]

        assert "승인" in approve_btn.text
        assert "approve:alert-123" in approve_btn.callback_data
        assert "거절" in reject_btn.text
        assert "reject:alert-123" in reject_btn.callback_data

    def test_parse_callback_data_approve(self, telegram_service):
        """parse_callback_data should parse approve action."""
        result = telegram_service.parse_callback_data("approve:alert-123")
        assert result == ("approve", "alert-123")

    def test_parse_callback_data_reject(self, telegram_service):
        """parse_callback_data should parse reject action."""
        result = telegram_service.parse_callback_data("reject:alert-456")
        assert result == ("reject", "alert-456")

    def test_parse_callback_data_invalid_format(self, telegram_service):
        """parse_callback_data should return None for invalid format."""
        assert telegram_service.parse_callback_data("invalid") is None
        assert telegram_service.parse_callback_data("") is None
        assert telegram_service.parse_callback_data("unknown:123") is None

    def test_get_deep_link_url(self, telegram_service):
        """get_deep_link_url should generate correct URL."""
        url = telegram_service.get_deep_link_url("test-token-123")
        assert url == "https://t.me/test_bot?start=test-token-123"

    def test_get_deep_link_url_without_username(self, mock_settings):
        """get_deep_link_url should raise error without bot username."""
        mock_settings.telegram_bot_username = ""
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings
            with pytest.raises(ValueError, match="not configured"):
                service.get_deep_link_url("test-token")


class TestTelegramServiceAsync:
    """Async tests for TelegramService methods."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for tests."""
        settings = MagicMock()
        settings.telegram_enabled = True
        settings.telegram_bot_token = "test-bot-token"
        settings.telegram_bot_username = "test_bot"
        return settings

    @pytest.fixture
    def telegram_service(self, mock_settings):
        """Create TelegramService with mocked bot."""
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings
            service._bot = AsyncMock()
            return service

    @pytest.mark.anyio
    async def test_send_alert_success(self, telegram_service):
        """send_alert should send message and return info."""
        telegram_service._bot.send_message = AsyncMock(
            return_value=MagicMock(message_id=12345)
        )

        alert = AlertInfo(
            alert_id="alert-123",
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.85,
            current_price=72500.0,
            target_price=79000.0,
            stop_loss_price=68000.0,
            reasoning=["RSI < 30"],
            created_at=datetime.now(UTC),
        )

        result = await telegram_service.send_alert("123456789", alert)

        assert result is not None
        assert result["message_id"] == 12345
        assert result["chat_id"] == "123456789"
        assert result["alert_id"] == "alert-123"
        telegram_service._bot.send_message.assert_called_once()

    @pytest.mark.anyio
    async def test_send_alert_when_disabled(self, mock_settings):
        """send_alert should return None when disabled."""
        mock_settings.telegram_enabled = False
        with patch(
            "app.services.telegram_service.get_settings",
            return_value=mock_settings,
        ):
            service = TelegramService()
            service.settings = mock_settings

            alert = AlertInfo(
                alert_id="alert-123",
                stock_code="005930",
                stock_name="삼성전자",
                signal="BUY",
                confidence=0.85,
                current_price=72500.0,
                target_price=None,
                stop_loss_price=None,
                reasoning=[],
                created_at=datetime.now(UTC),
            )

            result = await service.send_alert("123456789", alert)
            assert result is None

    @pytest.mark.anyio
    async def test_answer_callback_success(self, telegram_service):
        """answer_callback should answer the callback query."""
        telegram_service._bot.answer_callback_query = AsyncMock()

        result = await telegram_service.answer_callback(
            "callback-123",
            "Test message",
            show_alert=True,
        )

        assert result is True
        telegram_service._bot.answer_callback_query.assert_called_once_with(
            callback_query_id="callback-123",
            text="Test message",
            show_alert=True,
        )

    @pytest.mark.anyio
    async def test_edit_message_after_action_approved(self, telegram_service):
        """edit_message_after_action should update message for approved."""
        telegram_service._bot.edit_message_text = AsyncMock()

        result = await telegram_service.edit_message_after_action(
            "123456789",
            12345,
            "approved",
            "Order executed",
        )

        assert result is True
        call_args = telegram_service._bot.edit_message_text.call_args
        assert "주문 실행 완료" in call_args.kwargs["text"]
        assert call_args.kwargs["reply_markup"] is None

    @pytest.mark.anyio
    async def test_edit_message_after_action_rejected(self, telegram_service):
        """edit_message_after_action should update message for rejected."""
        telegram_service._bot.edit_message_text = AsyncMock()

        result = await telegram_service.edit_message_after_action(
            "123456789",
            12345,
            "rejected",
            "User rejected",
        )

        assert result is True
        call_args = telegram_service._bot.edit_message_text.call_args
        assert "알림 거절됨" in call_args.kwargs["text"]

    @pytest.mark.anyio
    async def test_send_link_success_message(self, telegram_service):
        """send_link_success_message should send success message."""
        telegram_service._bot.send_message = AsyncMock()

        result = await telegram_service.send_link_success_message("123456789")

        assert result is True
        call_args = telegram_service._bot.send_message.call_args
        assert "연동 완료" in call_args.kwargs["text"]
        assert call_args.kwargs["parse_mode"] == "HTML"

    @pytest.mark.anyio
    async def test_send_error_message(self, telegram_service):
        """send_error_message should send error message."""
        telegram_service._bot.send_message = AsyncMock()

        result = await telegram_service.send_error_message(
            "123456789",
            "Something went wrong",
        )

        assert result is True
        call_args = telegram_service._bot.send_message.call_args
        assert "⚠️" in call_args.kwargs["text"]
        assert "Something went wrong" in call_args.kwargs["text"]


class TestGetTelegramService:
    """Tests for get_telegram_service singleton function."""

    def test_get_telegram_service_returns_singleton(self):
        """get_telegram_service should return the same instance."""
        import app.services.telegram_service as module

        # Reset singleton
        module._telegram_service = None

        with patch(
            "app.services.telegram_service.get_settings",
        ) as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.telegram_enabled = False
            mock_settings.telegram_bot_token = ""
            mock_get_settings.return_value = mock_settings

            service1 = get_telegram_service()
            service2 = get_telegram_service()

            assert service1 is service2
