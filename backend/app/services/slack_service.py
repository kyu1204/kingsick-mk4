import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_URL_PATTERN = re.compile(
    r"^https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+$"
)

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]


@dataclass
class SlackAlertInfo:
    alert_id: str
    stock_code: str
    stock_name: str
    signal: str
    confidence: float
    current_price: float
    target_price: float | None
    stop_loss_price: float | None
    reasoning: list[str]
    created_at: datetime


class SlackServiceError(Exception):
    pass


class InvalidWebhookUrlError(SlackServiceError):
    pass


class SlackSendError(SlackServiceError):
    pass


class SlackService:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def validate_webhook_url(self, url: str) -> bool:
        return bool(WEBHOOK_URL_PATTERN.match(url))

    def mask_webhook_url(self, url: str) -> str:
        if not url:
            return ""
        parts = url.split("/services/")
        if len(parts) != 2:
            return url[:30] + "****"
        service_parts = parts[1].split("/")
        if len(service_parts) >= 3:
            return f"{parts[0]}/services/{service_parts[0][:4]}****/{service_parts[1][:4]}****/****"
        return url[:30] + "****"

    def _format_alert_blocks(self, alert: SlackAlertInfo) -> list[dict]:
        signal_emoji = ":large_green_circle:" if alert.signal == "BUY" else ":red_circle:"
        signal_text = "매수" if alert.signal == "BUY" else "매도"

        fields = [
            {"type": "mrkdwn", "text": f"*종목:* {alert.stock_name} ({alert.stock_code})"},
            {"type": "mrkdwn", "text": f"*신호:* {signal_emoji} {signal_text} ({alert.confidence:.0%})"},
            {"type": "mrkdwn", "text": f"*현재가:* {alert.current_price:,.0f}원"},
        ]

        if alert.target_price:
            fields.append({"type": "mrkdwn", "text": f"*목표가:* {alert.target_price:,.0f}원"})
        if alert.stop_loss_price:
            fields.append({"type": "mrkdwn", "text": f"*손절가:* {alert.stop_loss_price:,.0f}원"})

        reasoning_text = "*판단 근거:*\n" + "\n".join(f"• {r}" for r in alert.reasoning)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":bell: 매매 알림",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": fields,
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": reasoning_text,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":clock1: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    }
                ],
            },
        ]
        return blocks

    async def send_alert(self, webhook_url: str, alert: SlackAlertInfo) -> bool:
        if not self.validate_webhook_url(webhook_url):
            raise InvalidWebhookUrlError("Invalid Slack webhook URL format")

        blocks = self._format_alert_blocks(alert)
        payload = {
            "blocks": blocks,
            "text": f"매매 알림: {alert.stock_name} ({alert.stock_code}) - {alert.signal}",
        }

        return await self._send_with_retry(webhook_url, payload)

    async def send_test_message(self, webhook_url: str) -> bool:
        if not self.validate_webhook_url(webhook_url):
            raise InvalidWebhookUrlError("Invalid Slack webhook URL format")

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: KingSick 연동 테스트",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Slack 연동이 정상적으로 설정되었습니다.\n매매 알림을 이 채널에서 받게 됩니다.",
                    },
                },
            ],
            "text": "KingSick Slack 연동 테스트",
        }

        return await self._send_with_retry(webhook_url, payload)

    async def _send_with_retry(self, webhook_url: str, payload: dict) -> bool:
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(webhook_url, json=payload)
                if response.status_code == 200:
                    logger.info("Slack message sent successfully")
                    return True
                logger.warning(
                    f"Slack API returned {response.status_code}: {response.text}"
                )
                last_error = SlackSendError(
                    f"Slack API returned {response.status_code}"
                )
            except httpx.TimeoutException as e:
                logger.warning(f"Slack request timeout (attempt {attempt + 1}): {e}")
                last_error = e
            except httpx.HTTPError as e:
                logger.warning(f"Slack HTTP error (attempt {attempt + 1}): {e}")
                last_error = e

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[attempt])

        raise SlackSendError(f"Failed to send Slack message after {MAX_RETRIES} attempts") from last_error


_slack_service: SlackService | None = None


def get_slack_service() -> SlackService:
    global _slack_service
    if _slack_service is None:
        _slack_service = SlackService()
    return _slack_service
