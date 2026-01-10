from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.slack_service import (
    InvalidWebhookUrlError,
    SlackAlertInfo,
    SlackSendError,
    SlackService,
    get_slack_service,
)

# Fake webhook URL for testing (not a real Slack URL)
FAKE_WEBHOOK_URL = "https://hooks.slack.com/services/TEST00001/TEST00002/testtoken123456789012"
FAKE_WEBHOOK_URL_HTTP = "http://hooks.slack.com/services/TEST00001/TEST00002/testtoken123456789012"


class TestSlackAlertInfo:
    def test_create_alert_info(self):
        alert = SlackAlertInfo(
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
        assert alert.signal == "BUY"
        assert alert.confidence == 0.85

    def test_alert_info_with_none_prices(self):
        alert = SlackAlertInfo(
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


class TestSlackService:
    @pytest.fixture
    def slack_service(self):
        return SlackService()

    def test_validate_webhook_url_valid(self, slack_service):
        assert slack_service.validate_webhook_url(FAKE_WEBHOOK_URL) is True

    def test_validate_webhook_url_invalid_domain(self, slack_service):
        invalid_url = "https://example.com/hooks"
        assert slack_service.validate_webhook_url(invalid_url) is False

    def test_validate_webhook_url_invalid_format(self, slack_service):
        invalid_url = "https://hooks.slack.com/services/invalid"
        assert slack_service.validate_webhook_url(invalid_url) is False

    def test_validate_webhook_url_http_not_https(self, slack_service):
        assert slack_service.validate_webhook_url(FAKE_WEBHOOK_URL_HTTP) is False

    def test_mask_webhook_url(self, slack_service):
        masked = slack_service.mask_webhook_url(FAKE_WEBHOOK_URL)
        assert "TEST****" in masked
        assert "****" in masked
        assert "testtoken123456789012" not in masked

    def test_mask_webhook_url_empty(self, slack_service):
        assert slack_service.mask_webhook_url("") == ""

    def test_mask_webhook_url_invalid(self, slack_service):
        invalid_url = "https://example.com/some/long/path/here"
        masked = slack_service.mask_webhook_url(invalid_url)
        assert "****" in masked

    @pytest.mark.asyncio
    async def test_send_alert_invalid_url(self, slack_service):
        alert = SlackAlertInfo(
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
        with pytest.raises(InvalidWebhookUrlError):
            await slack_service.send_alert("invalid-url", alert)

    @pytest.mark.asyncio
    async def test_send_test_message_invalid_url(self, slack_service):
        with pytest.raises(InvalidWebhookUrlError):
            await slack_service.send_test_message("invalid-url")

    @pytest.mark.asyncio
    async def test_send_alert_success(self, slack_service):
        alert = SlackAlertInfo(
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

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(slack_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await slack_service.send_alert(FAKE_WEBHOOK_URL, alert)
            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_failure(self, slack_service):
        alert = SlackAlertInfo(
            alert_id="alert-123",
            stock_code="005930",
            stock_name="삼성전자",
            signal="BUY",
            confidence=0.85,
            current_price=72500.0,
            target_price=None,
            stop_loss_price=None,
            reasoning=["RSI < 30"],
            created_at=datetime.now(UTC),
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(slack_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            with pytest.raises(SlackSendError):
                await slack_service.send_alert(FAKE_WEBHOOK_URL, alert)

    @pytest.mark.asyncio
    async def test_send_test_message_success(self, slack_service):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(slack_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await slack_service.send_test_message(FAKE_WEBHOOK_URL)
            assert result is True

    @pytest.mark.asyncio
    async def test_close(self, slack_service):
        mock_client = AsyncMock()
        mock_client.is_closed = False
        slack_service._client = mock_client

        await slack_service.close()
        mock_client.aclose.assert_called_once()
        assert slack_service._client is None

    def test_format_alert_blocks_buy(self, slack_service):
        alert = SlackAlertInfo(
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
        blocks = slack_service._format_alert_blocks(alert)
        assert len(blocks) > 0
        header = blocks[0]
        assert header["type"] == "header"
        assert ":bell:" in header["text"]["text"]

    def test_format_alert_blocks_sell(self, slack_service):
        alert = SlackAlertInfo(
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
        blocks = slack_service._format_alert_blocks(alert)
        section = blocks[1]
        assert section["type"] == "section"
        fields_text = str(section["fields"])
        assert ":red_circle:" in fields_text


class TestGetSlackService:
    def test_get_slack_service_singleton(self):
        service1 = get_slack_service()
        service2 = get_slack_service()
        assert service1 is service2
