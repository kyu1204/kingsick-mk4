# Phase 3 Task 3-4: Slack Webhook 연동 설계

> **작성일**: 2026-01-10  
> **상태**: 설계 완료  
> **우선순위**: P2

---

## 1. 개요

### 1.1 목적
ALERT 모드에서 생성된 매매 알림을 Slack Incoming Webhook으로 전송하여, 사용자가 다양한 채널에서 알림을 받을 수 있도록 함.

### 1.2 주요 기능
- 매매 알림 메시지 전송 (종목, 신호, 신뢰도, 판단 근거)
- Slack Block Kit을 활용한 풍부한 메시지 포맷
- 단방향 알림 (Telegram과 달리 버튼 상호작용 없음)
- Webhook URL 저장 및 관리

### 1.3 Telegram과의 차이점

| 항목 | Telegram | Slack |
|------|----------|-------|
| 통신 방식 | 양방향 (Webhook + Callback) | 단방향 (Webhook만) |
| 사용자 상호작용 | 승인/거절 버튼 | 없음 (알림만) |
| 연동 방식 | Deep Link + Bot Token | Incoming Webhook URL |
| 설정 복잡도 | 높음 (Bot 생성 필요) | 낮음 (URL만 입력) |

### 1.4 기술 스택
- **통신**: HTTP POST (httpx)
- **메시지 포맷**: Slack Block Kit
- **보안**: HTTPS only (Slack 정책)

---

## 2. 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                      Backend Server                          │
├─────────────────────────────────────────────────────────────┤
│  1. SlackService (app/services/slack_service.py)            │
│     - send_alert(): 알림 메시지 전송                         │
│     - send_test_message(): 연결 테스트                       │
│     - validate_webhook_url(): URL 형식 검증                  │
│                                                              │
│  2. Settings API (app/api/settings.py 또는 slack.py)        │
│     POST /api/v1/settings/slack   - Webhook URL 저장         │
│     GET  /api/v1/settings/slack   - Webhook 상태 조회        │
│     POST /api/v1/settings/slack/test - 테스트 메시지 전송    │
│     DELETE /api/v1/settings/slack - Webhook 삭제             │
│                                                              │
│  3. TradingEngine 연동                                       │
│     - 알림 생성 시 Slack으로도 전송                          │
└─────────────────────────────────────────────────────────────┘
          ↓ HTTPS POST
┌─────────────────────────────────────────────────────────────┐
│                    Slack Servers                             │
└─────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────┐
│                    User's Slack Channel                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 알림 흐름

```
TradingEngine (알림 생성)
    ↓
SlackService.send_alert()
    ↓ HTTP POST
Slack Webhook URL
    ↓
사용자 Slack 채널에 메시지 표시
```

---

## 3. 데이터 모델

### 3.1 User 모델 확장

```python
# backend/app/models/user.py

class User(Base):
    # 기존 필드...

    # Slack 연동 필드 추가
    slack_webhook_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
```

> **Note**: Telegram과 달리 별도 테이블이 필요 없음 (단순 URL 저장)

---

## 4. API 엔드포인트

### 4.1 엔드포인트 목록

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| POST | /api/v1/settings/slack | Webhook URL 저장 | JWT |
| GET | /api/v1/settings/slack | Webhook 상태 조회 | JWT |
| POST | /api/v1/settings/slack/test | 테스트 메시지 전송 | JWT |
| DELETE | /api/v1/settings/slack | Webhook 삭제 | JWT |

### 4.2 상세 스펙

#### POST /api/v1/settings/slack

```json
// Request
{
    "webhook_url": "https://hooks.slack.com/services/YOUR_TEAM_ID/YOUR_BOT_ID/YOUR_TOKEN"
}

// Response 200
{
    "success": true,
    "message": "Slack webhook configured successfully"
}

// Response 400
{
    "detail": "Invalid Slack webhook URL format"
}
```

#### GET /api/v1/settings/slack

```json
// Response 200 (연동됨)
{
    "configured": true,
    "webhook_url_masked": "https://hooks.slack.com/services/T****/B****/****"
}

// Response 200 (미연동)
{
    "configured": false,
    "webhook_url_masked": null
}
```

#### POST /api/v1/settings/slack/test

```json
// Response 200
{
    "success": true,
    "message": "Test message sent successfully"
}

// Response 400
{
    "detail": "Slack webhook is not configured"
}

// Response 502
{
    "detail": "Failed to send message to Slack"
}
```

---

## 5. SlackService 구현

### 5.1 클래스 구조

```python
# backend/app/services/slack_service.py

class SlackService:
    """Service for Slack webhook operations."""

    WEBHOOK_URL_PATTERN = r"^https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+$"

    async def send_alert(self, webhook_url: str, alert: AlertInfo) -> bool:
        """Send a trading alert to Slack."""
        ...

    async def send_test_message(self, webhook_url: str) -> bool:
        """Send a test message to verify webhook."""
        ...

    def validate_webhook_url(self, url: str) -> bool:
        """Validate Slack webhook URL format."""
        ...

    def mask_webhook_url(self, url: str) -> str:
        """Mask webhook URL for display."""
        ...
```

### 5.2 메시지 포맷 (Block Kit)

```python
def _format_alert_blocks(self, alert: AlertInfo) -> list[dict]:
    """Format alert as Slack Block Kit blocks."""
    signal_emoji = ":large_green_circle:" if alert.signal == "BUY" else ":red_circle:"
    signal_text = "매수" if alert.signal == "BUY" else "매도"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":bell: 매매 알림",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*종목:* {alert.stock_name} ({alert.stock_code})"},
                {"type": "mrkdwn", "text": f"*신호:* {signal_emoji} {signal_text} ({alert.confidence:.0%})"},
                {"type": "mrkdwn", "text": f"*현재가:* {alert.current_price:,.0f}원"},
                {"type": "mrkdwn", "text": f"*목표가:* {alert.target_price:,.0f}원" if alert.target_price else "*목표가:* -"},
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*판단 근거:*\n" + "\n".join(f"• {r}" for r in alert.reasoning)
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":clock1: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}"}
            ]
        }
    ]
    return blocks
```

---

## 6. 에러 처리

### 6.1 에러 시나리오

| 상황 | HTTP 상태 | 응답 |
|------|-----------|------|
| 잘못된 Webhook URL 형식 | 400 | "Invalid Slack webhook URL format" |
| Webhook 미설정 시 테스트 | 400 | "Slack webhook is not configured" |
| Slack API 응답 실패 | 502 | "Failed to send message to Slack" |
| 네트워크 타임아웃 | 504 | "Request to Slack timed out" |

### 6.2 재시도 로직

```python
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds

async def send_with_retry(self, webhook_url: str, payload: dict) -> bool:
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return True
        except httpx.TimeoutException:
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(RETRY_DELAYS[attempt])
    return False
```

---

## 7. Frontend UI

### 7.1 SlackSettings 컴포넌트

```tsx
// frontend/components/settings/SlackSettings.tsx

export function SlackSettings() {
    // 상태 관리
    const [webhookUrl, setWebhookUrl] = useState("");
    const [isConfigured, setIsConfigured] = useState(false);
    const [isTesting, setIsTesting] = useState(false);

    // 기능
    // - Webhook URL 입력 폼
    // - 저장 버튼
    // - 테스트 메시지 전송 버튼
    // - 연결 해제 버튼
}
```

### 7.2 UI 요소

| 요소 | 설명 |
|------|------|
| Webhook URL 입력 필드 | 마스킹된 URL 표시 또는 입력 |
| 저장 버튼 | URL 저장 API 호출 |
| 테스트 버튼 | 테스트 메시지 전송 |
| 연결 해제 버튼 | Webhook 삭제 |
| 상태 배지 | 연동됨/미연동 표시 |

---

## 8. 구현 Task

| # | Task | 설명 | 예상 파일 |
|---|------|------|----------|
| 3-4-1 | User 모델 확장 | slack_webhook_url 필드 + 마이그레이션 | models/user.py, alembic/ |
| 3-4-2 | SlackService | 메시지 전송 로직 | services/slack_service.py |
| 3-4-3 | API 엔드포인트 | Slack 설정 CRUD | api/slack.py |
| 3-4-4 | TradingEngine 연동 | 알림 시 Slack 전송 | services/trading_engine.py |
| 3-4-5 | Frontend UI | Slack 설정 컴포넌트 | components/settings/SlackSettings.tsx |
| 3-4-6 | API 클라이언트 | Slack API 함수 | lib/api/slack.ts |
| 3-4-7 | 테스트 작성 | 단위/통합 테스트 | tests/ |

### 구현 순서

```
3-4-1 → 3-4-2 → 3-4-3 → 3-4-4 → 3-4-5 → 3-4-6 → 3-4-7
```

---

## 9. Slack Webhook 설정 방법 (사용자 가이드)

### 9.1 Incoming Webhook 생성

1. Slack 워크스페이스에서 앱 관리 페이지로 이동
2. "Incoming Webhooks" 검색 또는 "새 앱 만들기" 선택
3. "Incoming Webhooks" 활성화
4. "Add New Webhook to Workspace" 클릭
5. 알림 받을 채널 선택
6. 생성된 Webhook URL 복사

### 9.2 Webhook URL 형식

```
https://hooks.slack.com/services/YOUR_TEAM_ID/YOUR_BOT_ID/YOUR_SECRET_TOKEN
```

- `YOUR_TEAM_ID`: Team ID (T로 시작)
- `YOUR_BOT_ID`: Bot ID (B로 시작)
- `XXXXXXXX...`: Secret Token

---

## 10. 참고 자료

- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder)
- [Slack Message Formatting](https://api.slack.com/reference/surfaces/formatting)
