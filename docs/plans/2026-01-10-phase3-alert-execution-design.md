# Phase 3 Task 3-5: Alert Approval → Order Execution 설계

> **작성일**: 2026-01-10
> **상태**: 구현 완료 (개선 필요)
> **우선순위**: P1

---

## 1. 개요

### 1.1 목적
ALERT 모드에서 Telegram으로 전송된 매매 알림을 사용자가 승인하면, KIS API를 통해 실제 주문을 실행하고 결과를 알려주는 End-to-End 플로우 구현.

### 1.2 핵심 플로우
```
TradingEngine (ALERT mode)
    ↓ AlertInfo 생성
    ↓ _pending_alerts에 저장
    ↓ TelegramService.send_alert()
Telegram 사용자
    ↓ ✅승인 버튼 클릭
Webhook (/api/v1/telegram/webhook)
    ↓ callback_query 처리
    ↓ trading_engine.approve_alert(alert_id)
KISApiClient.place_order()
    ↓ 주문 실행
결과 메시지 편집 (성공/실패)
```

### 1.3 구현 상태

| 컴포넌트 | 상태 | 파일 |
|----------|------|------|
| approve_alert() | ✅ 완료 | trading_engine.py:632-677 |
| reject_alert() | ✅ 완료 | trading_engine.py:679-698 |
| Webhook 콜백 처리 | ✅ 완료 | telegram.py:318-412 |
| KIS place_order() | ✅ 완료 | kis_api.py:366-438 |
| 결과 메시지 편집 | ✅ 완료 | telegram_service.py |

---

## 2. 아키텍처

### 2.1 전체 시퀀스

```
┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐
│ Trading │    │   Telegram   │    │   Backend   │    │  KIS API  │
│ Engine  │    │     User     │    │   Webhook   │    │           │
└────┬────┘    └──────┬───────┘    └──────┬──────┘    └─────┬─────┘
     │                │                   │                  │
     │ 1. 매매 신호 감지                   │                  │
     │────────────────────────────────────>│                  │
     │ 2. AlertInfo 생성                   │                  │
     │ 3. _pending_alerts 저장             │                  │
     │ 4. send_alert()                     │                  │
     │                │<───────────────────│                  │
     │                │ 5. 알림 메시지 수신  │                  │
     │                │                    │                  │
     │                │ 6. ✅승인 클릭       │                  │
     │                │────────────────────>│                  │
     │                │                    │ 7. approve_alert()
     │                │                    │ 8. _pending_alerts.pop()
     │                │                    │────────────────────>│
     │                │                    │  9. place_order()   │
     │                │                    │<────────────────────│
     │                │                    │ 10. OrderResult     │
     │                │<───────────────────│                     │
     │                │ 11. 결과 메시지 편집 │                     │
```

### 2.2 AlertInfo 구조

```python
@dataclass
class AlertInfo:
    alert_id: str           # UUID
    user_id: str
    stock_code: str         # "005930"
    stock_name: str         # "삼성전자"
    signal: TradingSignal   # 매매 신호 상세
    signal_type: SignalType # BUY or SELL
    current_price: float
    suggested_quantity: int
    position: Position | None  # SELL 시에만 사용
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

### 2.3 Pending Alerts 저장소

```python
# trading_engine.py
class TradingEngine:
    _pending_alerts: dict[str, AlertInfo] = {}  # alert_id -> AlertInfo
```

**현재 한계:**
- 메모리 내 저장 (서버 재시작 시 유실)
- 타임아웃 메커니즘 없음 (5분 만료 미구현)

---

## 3. approve_alert() 구현

### 3.1 현재 구현 (trading_engine.py:632-677)

```python
async def approve_alert(self, alert_id: str) -> dict[str, str | int | float | bool] | None:
    """Approve a pending alert and execute the order."""
    # 1. pending alerts에서 alert 제거 (pop)
    alert = self._pending_alerts.pop(alert_id, None)
    if not alert:
        logger.warning(f"Alert not found: {alert_id}")
        return None

    # 2. 신호 타입에 따라 주문 실행
    if alert.signal_type == SignalType.BUY:
        order_result = await self._kis_client.place_order(
            stock_code=alert.stock_code,
            side=OrderSide.BUY,
            quantity=alert.suggested_quantity,
            price=None,  # Market order
        )
    else:  # SELL
        order_result = await self._kis_client.place_order(
            stock_code=alert.stock_code,
            side=OrderSide.SELL,
            quantity=alert.suggested_quantity,
            price=None,  # Market order
        )

    # 3. 결과 반환
    if order_result.success:
        return {
            "success": True,
            "order_id": order_result.order_id or "",
            "stock_code": alert.stock_code,
            "stock_name": alert.stock_name,
            "action": "매수" if alert.signal_type == SignalType.BUY else "매도",
            "quantity": alert.suggested_quantity,
            "price": alert.current_price,
        }
    else:
        raise Exception(order_result.message or "Order execution failed")
```

### 3.2 Webhook에서의 호출 (telegram.py:353-384)

```python
if action == "approve":
    try:
        result = await trading_engine.approve_alert(alert_id)  # await 필수!
        if result:
            await telegram_service.answer_callback(
                callback_id,
                "✅ 주문이 실행되었습니다!",
            )
            # 메시지 편집 (주문 결과 표시)
            await telegram_service.edit_message_after_action(
                chat_id, message_id, "approved", result_text
            )
        else:
            # Alert not found (이미 처리됨 or 만료)
            await telegram_service.answer_callback(
                callback_id,
                "⚠️ 알림을 찾을 수 없거나 이미 처리되었습니다.",
                show_alert=True,
            )
    except Exception as e:
        # 주문 실행 실패
        await telegram_service.answer_callback(
            callback_id,
            f"❌ 주문 실행 실패: {str(e)}",
            show_alert=True,
        )
```

---

## 4. reject_alert() 구현

### 4.1 현재 구현 (trading_engine.py:679-698)

```python
def reject_alert(self, alert_id: str) -> dict[str, str | int] | None:
    """Reject a pending alert without executing."""
    alert = self._pending_alerts.pop(alert_id, None)
    if alert:
        logger.info(f"Alert rejected: {alert.stock_code}, alert_id={alert_id}")
        return {
            "stock_code": alert.stock_code,
            "stock_name": alert.stock_name,
            "action": "매수" if alert.signal_type == SignalType.BUY else "매도",
            "quantity": alert.suggested_quantity,
        }
    logger.warning(f"Alert not found for rejection: {alert_id}")
    return None
```

**Note**: `reject_alert()`는 동기 함수 (DB 접근 없음)

---

## 5. 에러 핸들링

### 5.1 에러 시나리오

| 시나리오 | 처리 방법 |
|----------|----------|
| Alert not found | `⚠️ 알림을 찾을 수 없거나 이미 처리되었습니다` |
| KIS API 인증 실패 | `❌ 주문 실행 실패: Not authenticated` |
| 주문 거부 (잔고 부족 등) | `❌ 주문 실행 실패: {msg1}` |
| 네트워크 오류 | `❌ 주문 실행 실패: Network error after 3 retries` |
| User not linked | `연동된 계정을 찾을 수 없습니다` |

### 5.2 KIS API 에러 응답

```python
@dataclass
class OrderResult:
    success: bool
    order_id: str | None
    message: str        # 에러 메시지
    status: OrderStatus # PENDING, FILLED, FAILED, etc.
```

---

## 6. 개선 필요 사항

### 6.1 Alert Expiry (P1) ✅ 구현 완료

**문제**: 알림 생성 후 시간이 지나면 시장 상황이 변함. 5분 후에는 무효화 필요.

**상태**: ✅ 구현 완료 (2026-01-10)

**구현 내용**:
- `AlertExpiredError` 예외 클래스 추가
- `approve_alert()`에서 5분 만료 체크
- Webhook에서 만료 에러 처리 (별도 메시지 표시)
- `cleanup_expired_alerts()` 메서드 추가
- 테스트 5개 추가 (312 passed)

```python
# 구현된 코드
async def approve_alert(self, alert_id: str) -> dict | None:
    alert = self._pending_alerts.get(alert_id)
    if not alert:
        return None
    
    now = datetime.now(UTC)
    if now - alert.created_at > timedelta(minutes=ALERT_EXPIRY_MINUTES):
        self._pending_alerts.pop(alert_id, None)
        raise AlertExpiredError(f"알림이 만료되었습니다 ({ALERT_EXPIRY_MINUTES}분 초과)")
    
    # ... 주문 실행
```

**cleanup_expired_alerts()도 함께 구현됨**:
```python
def cleanup_expired_alerts(self) -> int:
    """Remove expired alerts from pending alerts."""
    now = datetime.now(UTC)
    expiry_threshold = timedelta(minutes=ALERT_EXPIRY_MINUTES)
    expired_ids = [
        aid for aid, alert in self._pending_alerts.items()
        if now - alert.created_at > expiry_threshold
    ]
    for alert_id in expired_ids:
        self._pending_alerts.pop(alert_id, None)
    return len(expired_ids)
```

### 6.2 영구 저장소 (P2)

**문제**: 서버 재시작 시 pending alerts 유실

**개선안**:
- Redis 사용 (TTL 지원)
- 또는 PostgreSQL + scheduled cleanup

### 6.3 주문 체결 확인 (P3)

**문제**: `place_order()`는 주문 접수만 확인, 실제 체결 여부는 별도 조회 필요

**개선안**:
```python
# 주문 후 체결 조회
order_result = await self._kis_client.place_order(...)
if order_result.success:
    # 잠시 대기 후 체결 확인 (선택적)
    await asyncio.sleep(1)
    filled = await self._kis_client.check_order_status(order_result.order_id)
```

### 6.4 동시성 처리 (P2)

**문제**: 같은 알림에 여러 번 클릭 시 race condition

**현재 완화**: `_pending_alerts.pop()` 사용으로 첫 클릭만 처리

**잠재적 문제**: 동시 요청 시 `pop()` 호출 전에 두 요청 모두 `get()` 통과 가능

**개선안**:
- 분산 락 (Redis lock)
- 또는 낙관적 락 (버전 체크)

---

## 7. 테스트

### 7.1 기존 테스트 커버리지

| 테스트 파일 | 테스트 수 | 커버리지 |
|------------|----------|----------|
| test_trading_engine.py | 43 tests | 94% |
| test_api_telegram.py | 18 tests | - |

### 7.2 추가 테스트 필요

```python
# test_trading_engine.py
class TestApproveAlert:
    async def test_approve_alert_success(self):
        """승인 시 주문 실행 및 결과 반환"""
        pass
    
    async def test_approve_alert_not_found(self):
        """존재하지 않는 alert_id"""
        pass
    
    async def test_approve_alert_order_failed(self):
        """KIS API 주문 실패"""
        pass
    
    async def test_approve_alert_expired(self):
        """만료된 알림 승인 시도 (개선 후)"""
        pass

class TestRejectAlert:
    def test_reject_alert_success(self):
        """거절 시 알림 제거"""
        pass
    
    def test_reject_alert_not_found(self):
        """존재하지 않는 alert_id"""
        pass
```

---

## 8. 버그 수정 이력

### 8.1 await 누락 버그 (2026-01-10)

**위치**: `telegram.py:355`

**문제**: `approve_alert()`는 async 함수인데 await 없이 호출

**수정 전**:
```python
result = trading_engine.approve_alert(alert_id)  # ❌ BUG
```

**수정 후**:
```python
result = await trading_engine.approve_alert(alert_id)  # ✅ FIXED
```

---

## 9. 다음 단계

### 즉시 (P1)
- [x] await 누락 버그 수정 ✅
- [ ] Alert expiry 구현 (5분 타임아웃)
- [ ] 만료 시 Telegram 메시지 자동 수정

### 추후 (P2/P3)
- [ ] Redis 영구 저장소 전환
- [ ] 주문 체결 확인 API 연동
- [ ] 동시성 처리 개선

---

## 10. 관련 문서

- [Telegram Bot 연동 설계](./2026-01-10-phase3-telegram-design.md)
- [Watchlist 설계](./2026-01-10-phase3-watchlist-design.md)
- [PROGRESS.md](./PROGRESS.md)
