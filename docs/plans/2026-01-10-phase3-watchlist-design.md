# Phase 3-1: Watchlist 설계 문서

> **작성일**: 2026-01-10
> **상태**: 승인됨
> **범위**: 종목 직접 지정 (Watchlist) 기능

---

## 개요

사용자가 관심 종목을 직접 등록하고, 종목별 매매 조건을 설정할 수 있는 Watchlist 기능 구현.

### 핵심 기능

- 종목 추가/수정/삭제
- 종목별 매매 설정 (목표가, 손절가, 수량)
- 활성화/비활성화 토글
- KIS API 종목 검색 자동완성
- Trading Engine 연동

### 제외 범위

- 그룹/분류 기능 (단일 목록으로 관리)
- AI 자동 스캔 (Phase 3-2에서 별도 구현)
- 종목별 전략 설정 (전역 BNF 전략 사용)

---

## 데이터 모델

### WatchlistItem 테이블

```sql
CREATE TABLE watchlist_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_code VARCHAR(6) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- 매매 설정
    target_price DECIMAL(12, 2),      -- 목표가 (nullable)
    stop_loss_price DECIMAL(12, 2),   -- 손절가 (nullable)
    quantity INTEGER,                  -- 매매 수량 (nullable)
    memo TEXT,                         -- 메모 (nullable)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_user_stock UNIQUE (user_id, stock_code),
    CONSTRAINT chk_target_price CHECK (target_price IS NULL OR target_price > 0),
    CONSTRAINT chk_stop_loss_price CHECK (stop_loss_price IS NULL OR stop_loss_price > 0),
    CONSTRAINT chk_quantity CHECK (quantity IS NULL OR quantity > 0)
);

CREATE INDEX idx_watchlist_user_active ON watchlist_items(user_id, is_active);
```

### SQLAlchemy 모델

```python
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    stock_code: Mapped[str] = mapped_column(String(6))
    stock_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)

    target_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int | None]
    memo: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint("user_id", "stock_code", name="uq_user_stock"),
    )
```

---

## API 엔드포인트

### Watchlist CRUD

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/watchlist` | 종목 추가 |
| GET | `/api/v1/watchlist` | 목록 조회 (현재가 포함) |
| GET | `/api/v1/watchlist/{id}` | 단일 조회 |
| PUT | `/api/v1/watchlist/{id}` | 수정 |
| DELETE | `/api/v1/watchlist/{id}` | 삭제 |
| PATCH | `/api/v1/watchlist/{id}/toggle` | 활성화 토글 |

### 종목 검색

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/stocks/search?q={keyword}` | 종목 검색 |

### Request/Response 스키마

#### POST /api/v1/watchlist

**Request:**
```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "target_price": 85000,
  "stop_loss_price": 70000,
  "quantity": 10,
  "memo": "실적 시즌 대비"
}
```

**Response (201):**
```json
{
  "id": 1,
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "is_active": true,
  "target_price": 85000,
  "stop_loss_price": 70000,
  "quantity": 10,
  "memo": "실적 시즌 대비",
  "created_at": "2026-01-10T09:00:00Z"
}
```

#### GET /api/v1/watchlist

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "is_active": true,
      "target_price": 85000,
      "stop_loss_price": 70000,
      "quantity": 10,
      "memo": "실적 시즌 대비",
      "current_price": 78000,
      "price_change": -2.5,
      "created_at": "2026-01-10T09:00:00Z",
      "updated_at": "2026-01-10T09:00:00Z"
    }
  ],
  "total": 1
}
```

#### GET /api/v1/stocks/search?q=삼성

**Response (200):**
```json
{
  "stocks": [
    {"code": "005930", "name": "삼성전자", "market": "KOSPI"},
    {"code": "000830", "name": "삼성물산", "market": "KOSPI"},
    {"code": "006400", "name": "삼성SDI", "market": "KOSPI"}
  ]
}
```

---

## Frontend UI

### 페이지 구조

```
/watchlist
├── Header: "Watchlist" + 종목 추가 버튼
├── WatchlistTable
│   ├── Columns: 종목코드 | 종목명 | 현재가 | 목표가 | 손절가 | 수량 | 활성화 | 액션
│   ├── 정렬: 종목명, 현재가, 등록일
│   └── 필터: 활성/비활성/전체
└── Empty State (종목 없을 때)
```

### 컴포넌트 구조

```
components/watchlist/
├── WatchlistTable.tsx        # 종목 목록 테이블
├── AddStockModal.tsx         # 종목 추가 모달
├── EditStockModal.tsx        # 종목 수정 모달
├── StockSearchInput.tsx      # 종목 검색 자동완성
├── ActiveToggle.tsx          # 활성화 스위치
└── DeleteConfirmDialog.tsx   # 삭제 확인 다이얼로그
```

### UI 흐름

1. **종목 추가**
   - "종목 추가" 버튼 클릭
   - 모달 열림 → 종목 검색 입력
   - 검색 결과에서 종목 선택
   - 매매 설정 입력 (선택사항)
   - 저장 → 목록에 추가

2. **종목 수정**
   - 행의 편집 버튼 클릭
   - 모달 열림 → 기존 설정 표시
   - 설정 변경 → 저장

3. **활성화 토글**
   - 스위치 클릭 → 즉시 API 호출
   - Optimistic update 적용

4. **종목 삭제**
   - 삭제 버튼 클릭
   - 확인 다이얼로그 → 확인 시 삭제

### 네비게이션

사이드바 메뉴 순서:
1. Dashboard
2. **Watchlist** (신규)
3. Portfolio
4. History
5. Settings

---

## Trading Engine 연동

### 매매 대상 종목 조회

```python
# services/trading_engine.py

async def get_trading_targets(self, user_id: int) -> list[WatchlistItem]:
    """사용자의 활성화된 Watchlist 종목 반환"""
    return await self.watchlist_service.get_active_items(user_id)
```

### Watchlist 설정 활용

매매 시 Watchlist에 설정된 값 우선 적용:

| Watchlist 설정 | 적용 대상 | 미설정 시 |
|----------------|-----------|-----------|
| `target_price` | 익절가 | Risk Manager 기본값 |
| `stop_loss_price` | 손절가 | Risk Manager 기본값 |
| `quantity` | 매매 수량 | Position Sizing 계산값 |

```python
async def execute_trade(self, item: WatchlistItem, signal: Signal):
    # Watchlist 설정 우선, 미설정 시 기본값
    stop_loss = item.stop_loss_price or self.risk_manager.default_stop_loss
    take_profit = item.target_price or self.risk_manager.default_take_profit
    quantity = item.quantity or self.risk_manager.calculate_position_size(...)
```

---

## KIS API 종목 검색

### 검색 메서드 추가

```python
# services/kis_api.py

async def search_stocks(self, keyword: str, limit: int = 20) -> list[StockInfo]:
    """
    종목명 또는 종목코드로 검색

    Args:
        keyword: 검색어 (최소 2글자)
        limit: 최대 결과 수

    Returns:
        [{code, name, market}] 목록
    """
```

### Frontend 검색 동작

- 최소 2글자 이상 입력 시 검색 실행
- 디바운스 300ms 적용
- 최대 20개 결과 표시
- 검색 중 로딩 표시

---

## 구현 Task 목록

### Backend (Task 3-1-1 ~ 3-1-5)

| # | Task | 산출물 | 테스트 |
|---|------|--------|--------|
| 3-1-1 | WatchlistItem 모델 | `models/watchlist.py`, Alembic | 모델 테스트 |
| 3-1-2 | Watchlist Repository | `repositories/watchlist.py` | CRUD 테스트 |
| 3-1-3 | Watchlist Service | `services/watchlist.py` | 비즈니스 로직 테스트 |
| 3-1-4 | Watchlist API 라우터 | `api/watchlist.py` | API 테스트 |
| 3-1-5 | 종목 검색 API | `api/stocks.py` | 검색 테스트 |

### Frontend (Task 3-1-6 ~ 3-1-8)

| # | Task | 산출물 |
|---|------|--------|
| 3-1-6 | API 클라이언트 | `lib/api/watchlist.ts` |
| 3-1-7 | Watchlist 페이지 | `app/watchlist/page.tsx` |
| 3-1-8 | 컴포넌트 구현 | `components/watchlist/*` |

### 연동 및 검증 (Task 3-1-9 ~ 3-1-10)

| # | Task | 산출물 |
|---|------|--------|
| 3-1-9 | Trading Engine 연동 | `services/trading_engine.py` 수정 |
| 3-1-10 | E2E 테스트 | 브라우저 테스트 완료 |

### 의존성

```
3-1-1 → 3-1-2 → 3-1-3 → 3-1-4 ──┐
                                 ├→ 3-1-6 → 3-1-7 → 3-1-8 → 3-1-10
3-1-5 ───────────────────────────┘
3-1-9 (3-1-3 완료 후 병렬 가능)
```

---

## 검증 체크리스트

- [ ] WatchlistItem 모델 생성 및 마이그레이션
- [ ] Watchlist CRUD API 동작 (curl 테스트)
- [ ] 종목 검색 API 동작
- [ ] Frontend Watchlist 페이지 렌더링
- [ ] 종목 추가/수정/삭제 동작
- [ ] 활성화/비활성화 토글 동작
- [ ] Trading Engine에서 Watchlist 종목 조회
- [ ] E2E 브라우저 테스트 완료
