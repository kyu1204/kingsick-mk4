# Phase 3 Task 3-3: Telegram Bot 연동 설계

> **작성일**: 2026-01-10
> **상태**: 설계 완료
> **우선순위**: P1

---

## 1. 개요

### 1.1 목적
ALERT 모드에서 생성된 매매 알림을 Telegram으로 전송하고, 사용자가 승인/거절 버튼을 클릭하여 즉시 주문을 실행할 수 있는 양방향 상호작용 시스템 구현.

### 1.2 주요 기능
- 매매 알림 메시지 전송 (종목, 신호, 신뢰도, 판단 근거)
- Inline Keyboard 버튼으로 승인/거절
- 버튼 클릭 시 즉시 주문 실행
- Deep Link를 통한 사용자별 Telegram 연동

### 1.3 기술 스택
- **라이브러리**: python-telegram-bot >= 21.0
- **통신 방식**: Webhook (프로덕션), Polling (로컬 개발)
- **보안**: secret_token으로 webhook 요청 검증

---

## 2. 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                      Backend Server                          │
├─────────────────────────────────────────────────────────────┤
│  1. TelegramService (app/services/telegram_service.py)      │
│     - send_alert(): 알림 메시지 + 승인/거절 버튼 전송         │
│     - answer_callback(): 버튼 클릭 응답                      │
│     - link_user(): Deep Link 토큰으로 chat_id 연결           │
│                                                              │
│  2. Webhook Endpoint (app/api/telegram.py)                  │
│     POST /api/v1/telegram/webhook                           │
│     - Update 객체 수신 → 라우팅                              │
│     - message: /start 명령 처리                              │
│     - callback_query: 버튼 클릭 처리                         │
│                                                              │
│  3. App Startup (app/main.py lifespan)                      │
│     - setWebhook 호출로 Telegram에 webhook URL 등록          │
│     - secret_token으로 요청 검증                             │
└─────────────────────────────────────────────────────────────┘
         ↑↓ HTTPS (port 443/8443)
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Servers                          │
└─────────────────────────────────────────────────────────────┘
         ↑↓
┌─────────────────────────────────────────────────────────────┐
│                    User's Telegram App                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Update 흐름

```
사용자 액션 (메시지/버튼 클릭)
    ↓
Telegram 서버
    ↓ POST (Update 객체)
Backend /api/v1/telegram/webhook
    ↓
TelegramService 처리
    ↓
응답 (메시지 수정, 알림 표시)
```

### 2.3 Deep Link 연동 흐름

```
1. Settings 페이지에서 "Telegram 연동" 클릭
2. POST /api/v1/telegram/link → TelegramLinkToken 생성 (10분 유효)
3. Deep Link 반환: https://t.me/KingSickBot?start={token}
4. 사용자가 Telegram에서 링크 클릭
5. Telegram이 /start {token} 명령 전송
6. Webhook에서 token 검증 → User.telegram_chat_id 저장
7. 연동 완료 메시지 전송
```

---

## 3. 데이터 모델

### 3.1 User 모델 확장

```python
# backend/app/models/user.py

class User(Base):
    # 기존 필드...

    # Telegram 연동 필드 추가
    telegram_chat_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True
    )
    telegram_linked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
```

### 3.2 TelegramLinkToken 모델

```python
# backend/app/models/telegram_link.py

class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    # 관계
    user: Mapped["User"] = relationship("User", back_populates="telegram_link_tokens")
```

---

## 4. API 엔드포인트

### 4.1 엔드포인트 목록

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| POST | /api/v1/telegram/link | 연동 토큰 생성 | JWT |
| GET | /api/v1/telegram/status | 연동 상태 확인 | JWT |
| DELETE | /api/v1/telegram/link | 연동 해제 | JWT |
| POST | /api/v1/telegram/webhook | Telegram 웹훅 | secret_token |

### 4.2 상세 스펙

#### POST /api/v1/telegram/link

```json
// Response 200
{
    "deep_link": "https://t.me/KingSickBot?start=abc123xyz",
    "expires_in": 600
}
```

#### GET /api/v1/telegram/status

```json
// Response 200 (연동됨)
{
    "linked": true,
    "linked_at": "2026-01-10T12:00:00Z"
}

// Response 200 (미연동)
{
    "linked": false,
    "linked_at": null
}
```

#### POST /api/v1/telegram/webhook

```python
# Headers
X-Telegram-Bot-Api-Secret-Token: {secret}

# Body: Telegram Update 객체
{
    "update_id": 123456789,
    "message": { ... },      # 또는
    "callback_query": { ... }
}
```

### 4.3 Webhook 내부 라우팅

```python
async def handle_webhook(update: Update):
    # 1. /start 명령 (Deep Link)
    if update.message and update.message.text.startswith("/start "):
        token = extract_token(update.message.text)
        await link_user(update.message.chat.id, token)
        await send_message(chat_id, "✅ KingSick 연동 완료!")

    # 2. 버튼 클릭 (승인/거절)
    elif update.callback_query:
        data = update.callback_query.data  # "approve:alert_id" or "reject:alert_id"
        action, alert_id = data.split(":")

        if action == "approve":
            result = await trading_engine.approve_alert(alert_id)
            text = f"✅ 주문 실행 완료\n체결가: {result.price}원"
        else:
            await trading_engine.reject_alert(alert_id)
            text = "❌ 알림 거절됨"

        # 필수: 버튼 로딩 해제
        await answer_callback_query(update.callback_query.id, text)
        # 메시지 수정 (버튼 제거)
        await edit_message(chat_id, message_id, updated_text)
```

---

## 5. 메시지 포맷

### 5.1 알림 메시지

```
🔔 <b>매매 알림</b>

📈 종목: 삼성전자 (005930)
📊 신호: 🟢 매수 (85%)
💰 현재가: 71,500원
🎯 목표가: 78,000원
🛑 손절가: 68,000원

<b>판단 근거:</b>
• RSI 과매도 (28.5)
• 볼린저밴드 하단 돌파
• 거래량 급증 (+150%)

⏰ 2026-01-10 14:30:25

[✅ 승인] [❌ 거절]
```

### 5.2 승인 완료 메시지

```
✅ <b>주문 실행 완료</b>

📈 종목: 삼성전자
📊 매수: 10주 × 71,500원
💵 총액: 715,000원

⏰ 2026-01-10 14:30:45
```

### 5.3 거절 메시지

```
❌ <b>알림 거절됨</b>

📈 종목: 삼성전자
📊 신호: 매수

⏰ 2026-01-10 14:30:40
```

### 5.4 Inline Keyboard

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_alert_keyboard(alert_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 승인", callback_data=f"approve:{alert_id}"),
            InlineKeyboardButton("❌ 거절", callback_data=f"reject:{alert_id}"),
        ]
    ])
```

---

## 6. 에러 처리

### 6.1 에러 시나리오

| 상황 | 처리 방식 |
|------|----------|
| 만료된 Deep Link 토큰 | "⚠️ 링크가 만료되었습니다. 새 링크를 생성해주세요." |
| 이미 사용된 토큰 | "⚠️ 이미 사용된 링크입니다." |
| 만료된 알림 승인 시도 | "⚠️ 알림이 만료되었습니다. (5분 경과)" |
| 이미 처리된 알림 | "ℹ️ 이미 처리된 알림입니다." |
| 주문 실행 실패 | "❌ 주문 실패: {error_message}\n수동으로 확인해주세요." |
| 연동 안 된 사용자의 /start | "❓ 올바른 연동 링크를 사용해주세요." |

### 6.2 알림 만료 정책

```python
ALERT_EXPIRY_MINUTES = 5  # 알림 생성 후 5분 경과 시 만료
```

### 6.3 Webhook 보안

```python
async def verify_telegram_request(request: Request) -> bool:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    return secret == settings.TELEGRAM_WEBHOOK_SECRET
```

### 6.4 재시도 로직

```python
MAX_RETRIES = 3
RETRY_DELAY = [1, 2, 4]  # 초 (exponential backoff)

async def send_alert_with_retry(chat_id: str, message: str, keyboard):
    for attempt in range(MAX_RETRIES):
        try:
            return await bot.send_message(chat_id, message, reply_markup=keyboard)
        except TelegramError as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Failed to send alert: {e}")
                raise
            await asyncio.sleep(RETRY_DELAY[attempt])
```

---

## 7. 환경 변수

```bash
# .env 추가
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=KingSickBot
TELEGRAM_WEBHOOK_SECRET=random_secret_string_for_verification
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/v1/telegram/webhook
```

---

## 8. 구현 Task

| # | Task | 설명 | 예상 파일 |
|---|------|------|----------|
| 3-3-1 | 의존성 추가 | python-telegram-bot 설치 | pyproject.toml |
| 3-3-2 | User 모델 확장 | telegram_chat_id 필드 + 마이그레이션 | models/user.py |
| 3-3-3 | TelegramLinkToken 모델 | Deep Link 토큰 모델 | models/telegram_link.py |
| 3-3-4 | TelegramService | 메시지 전송, 콜백 처리 | services/telegram_service.py |
| 3-3-5 | Telegram API 라우터 | webhook, link, status | api/telegram.py |
| 3-3-6 | TradingEngine 연동 | 알림 시 Telegram 전송 | services/trading_engine.py |
| 3-3-7 | Frontend Settings UI | Telegram 연동 버튼 | app/settings/page.tsx |
| 3-3-8 | 테스트 작성 | 단위/통합 테스트 | tests/ |

### 구현 순서

```
3-3-1 → 3-3-2 → 3-3-3 → 3-3-4 → 3-3-5 → 3-3-6 → 3-3-7 → 3-3-8
```

---

## 9. 로컬 개발 환경

### ngrok 사용

```bash
# 1. ngrok 설치 후 실행
ngrok http 8000

# 2. 출력된 HTTPS URL을 TELEGRAM_WEBHOOK_URL에 설정
# 예: https://abc123.ngrok.io/api/v1/telegram/webhook

# 3. 백엔드 서버 시작 (자동으로 setWebhook 호출)
uv run uvicorn app.main:app --reload
```

### Polling 모드 (대안)

로컬에서 webhook 없이 테스트하려면 polling 모드 사용 가능:

```python
# 로컬 전용 - 프로덕션에서는 webhook 사용
if settings.ENVIRONMENT == "development":
    await application.run_polling()
```

---

## 10. 참고 자료

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Inline Keyboards](https://core.telegram.org/bots/2-0-intro)
- [FreeCodeCamp - python-telegram-bot v20 Webhook](https://www.freecodecamp.org/news/how-to-build-and-deploy-python-telegram-bot-v20-webhooks/)
