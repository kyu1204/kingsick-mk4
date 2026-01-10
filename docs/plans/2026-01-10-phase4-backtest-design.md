# Phase 4: 백테스팅 및 AI 분석 설계서

> 작성일: 2026-01-10
> Phase: 4 (고도화)
> 선행 조건: Phase 1-3 완료

---

## 목차

1. [개요](#1-개요)
2. [Task 분해](#2-task-분해)
3. [Task 4-1: 과거 데이터 수집 및 저장](#3-task-4-1-과거-데이터-수집-및-저장)
4. [Task 4-2: 백테스팅 엔진](#4-task-4-2-백테스팅-엔진)
5. [Task 4-3: 결과 리포트](#5-task-4-3-결과-리포트)
6. [Task 4-4: 시장 상태 분석](#6-task-4-4-시장-상태-분석)
7. [Task 4-5: AI 추천 종목](#7-task-4-5-ai-추천-종목)
8. [Task 4-6: 신호 강도 시각화](#8-task-4-6-신호-강도-시각화)
9. [데이터 모델](#9-데이터-모델)
10. [API 설계](#10-api-설계)

---

## 1. 개요

### 1.1 Phase 4 목표

Phase 4는 KingSick의 **고도화** 단계로, 다음을 구현합니다:

1. **백테스팅 시스템**: 과거 데이터로 전략을 검증
2. **AI 분석 강화**: 시장 상태 분석, 종목 추천
3. **시각화 개선**: 신호 강도, 전략 성과 차트

### 1.2 기술적 고려사항

#### 시계열 데이터 저장
- **옵션 A (선택)**: PostgreSQL + 파티셔닝
  - 이미 PostgreSQL 사용 중
  - 추가 인프라 불필요
  - 파티션 테이블로 충분한 성능
  
- ~~옵션 B: TimescaleDB~~
  - Docker 이미지 변경 필요
  - 복잡도 증가
  - 현재 규모에서 과잉

#### 결정: PostgreSQL 파티셔닝 사용
- 월별 파티션 (예: stock_prices_2026_01)
- 인덱스: (stock_code, trade_date)
- 보관 기간: 5년 (약 1,250일 × 2,000종목 = 250만 rows/종목)

### 1.3 핵심 지표

| 지표 | 설명 | 계산 |
|------|------|------|
| 총 수익률 | 기간 전체 수익 | (최종자산 - 초기자산) / 초기자산 × 100 |
| CAGR | 연평균 복리 수익률 | (최종/초기)^(1/년수) - 1 |
| MDD | 최대 낙폭 | 고점 대비 최대 하락폭 |
| 샤프 비율 | 위험 대비 수익 | (수익률 - 무위험) / 변동성 |
| 승률 | 수익 거래 비율 | 이익 거래수 / 전체 거래수 × 100 |
| 손익비 | 평균 이익 vs 손실 | 평균 이익 / 평균 손실 |

---

## 2. Task 분해

### 우선순위

| # | Task | 우선순위 | 의존성 | 예상 공수 |
|---|------|----------|--------|-----------|
| 4-1 | 과거 데이터 수집 및 저장 | P1 | - | 4h |
| 4-2 | 백테스팅 엔진 | P1 | 4-1 | 6h |
| 4-3 | 결과 리포트 (수익률, MDD, 샤프비율) | P2 | 4-2 | 4h |
| 4-4 | 시장 상태 분석 페이지 | P2 | 4-1 | 4h |
| 4-5 | AI 추천 종목 | P3 | 4-1, 4-4 | 4h |
| 4-6 | 신호 강도 시각화 | P2 | - | 3h |

### 구현 순서

```
4-1 (데이터) ──┬──> 4-2 (백테스팅) ──> 4-3 (리포트)
              │
              └──> 4-4 (시장 분석) ──> 4-5 (AI 추천)

4-6 (신호 시각화) - 독립적, 병렬 진행 가능
```

---

## 3. Task 4-1: 과거 데이터 수집 및 저장

### 3.1 목표
- KIS API로 일봉 데이터 수집
- PostgreSQL에 효율적으로 저장
- 증분 업데이트 지원

### 3.2 데이터 모델

```python
# backend/app/models/stock_price.py

class StockPrice(Base):
    """주가 일봉 데이터"""
    __tablename__ = "stock_prices"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(10), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    
    # 복합 유니크 제약
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uq_stock_price"),
        Index("ix_stock_prices_code_date", "stock_code", "trade_date"),
    )
```

### 3.3 서비스

```python
# backend/app/services/price_history.py

class PriceHistoryService:
    """주가 히스토리 수집 및 조회 서비스"""
    
    async def fetch_and_store(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """KIS API에서 데이터 수집 후 DB 저장
        
        Returns:
            저장된 레코드 수
        """
    
    async def get_prices(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> list[StockPrice]:
        """기간별 주가 조회"""
    
    async def sync_latest(self, stock_code: str) -> int:
        """최신 데이터까지 증분 동기화"""
```

### 3.4 API 엔드포인트

```
POST /api/v1/backtest/prices/sync
  - Request: {"stock_code": "005930", "start_date": "2024-01-01", "end_date": "2026-01-10"}
  - Response: {"synced_count": 500}

GET /api/v1/backtest/prices/{stock_code}
  - Query: start_date, end_date
  - Response: list of OHLCV data
```

### 3.5 테스트

```python
# tests/unit/test_price_history.py

class TestPriceHistoryService:
    async def test_fetch_and_store_new_data(self): ...
    async def test_sync_latest_incremental(self): ...
    async def test_get_prices_date_range(self): ...
    async def test_duplicate_handling(self): ...
```

---

## 4. Task 4-2: 백테스팅 엔진

### 4.1 목표
- BNF 전략으로 과거 데이터 시뮬레이션
- 거래 비용 반영 (수수료, 세금)
- 일별 포트폴리오 추적

### 4.2 핵심 클래스

```python
# backend/app/services/backtest_engine.py

@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 10_000_000  # 1천만원
    commission_rate: float = 0.00015     # 0.015% (키움 기준)
    tax_rate: float = 0.0023             # 0.23% 거래세
    slippage: float = 0.001              # 0.1% 슬리피지
    
    # 리스크 설정
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    max_position_pct: float = 20.0       # 종목당 최대 비중


@dataclass
class BacktestTrade:
    """시뮬레이션 거래 기록"""
    trade_date: date
    stock_code: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    amount: float
    commission: float
    tax: float
    signal_reason: str


@dataclass
class BacktestResult:
    """백테스트 결과"""
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr: float
    mdd: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    trades: list[BacktestTrade]
    daily_returns: list[float]
    equity_curve: list[float]


class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(
        self,
        config: BacktestConfig,
        indicator_calculator: IndicatorCalculator,
        signal_generator: SignalGenerator,
    ):
        self.config = config
        self.indicator = indicator_calculator
        self.signal = signal_generator
    
    async def run(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        """백테스트 실행"""
```

### 4.3 시뮬레이션 로직

```python
async def run(self, stock_codes, start_date, end_date) -> BacktestResult:
    # 1. 데이터 로드
    price_data = await self._load_price_data(stock_codes, start_date, end_date)
    
    # 2. 일별 루프
    for current_date in self._trading_days(start_date, end_date):
        # 2.1 기존 포지션 평가 (손절/익절 체크)
        for position in self.positions:
            action = self._check_exit_conditions(position, current_date)
            if action:
                self._execute_sell(position, current_date, action.reason)
        
        # 2.2 신규 신호 생성
        for stock_code in stock_codes:
            if self._can_open_position():
                signal = self._generate_signal(stock_code, current_date)
                if signal.action == "BUY":
                    self._execute_buy(stock_code, current_date, signal)
        
        # 2.3 일별 자산 기록
        self._record_equity(current_date)
    
    # 3. 결과 계산
    return self._calculate_results()
```

### 4.4 API 엔드포인트

```
POST /api/v1/backtest/run
  - Request: {
      "stock_codes": ["005930", "000660"],
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "initial_capital": 10000000,
      "stop_loss_pct": 5.0,
      "take_profit_pct": 10.0
    }
  - Response: BacktestResult

GET /api/v1/backtest/results/{backtest_id}
  - Response: BacktestResult (저장된 결과 조회)
```

### 4.5 테스트

```python
# tests/unit/test_backtest_engine.py

class TestBacktestEngine:
    async def test_simple_buy_sell_cycle(self): ...
    async def test_stop_loss_triggered(self): ...
    async def test_take_profit_triggered(self): ...
    async def test_commission_and_tax_calculation(self): ...
    async def test_mdd_calculation(self): ...
    async def test_sharpe_ratio_calculation(self): ...
    async def test_equity_curve_tracking(self): ...
```

---

## 5. Task 4-3: 결과 리포트

### 5.1 목표
- 백테스트 결과 시각화
- PDF/이미지 리포트 생성 (옵션)
- Frontend 대시보드 통합

### 5.2 리포트 컴포넌트

```typescript
// frontend/components/backtest/BacktestReport.tsx

interface BacktestReportProps {
  result: BacktestResult;
}

export function BacktestReport({ result }: BacktestReportProps) {
  return (
    <div className="space-y-6">
      {/* 핵심 지표 카드 */}
      <MetricsCards result={result} />
      
      {/* 수익률 곡선 차트 */}
      <EquityCurveChart data={result.equity_curve} />
      
      {/* 월별 수익률 히트맵 */}
      <MonthlyReturnsHeatmap returns={result.monthly_returns} />
      
      {/* 거래 내역 테이블 */}
      <TradesTable trades={result.trades} />
      
      {/* 드로우다운 차트 */}
      <DrawdownChart data={result.drawdown_curve} />
    </div>
  );
}
```

### 5.3 차트 라이브러리

기존 Lightweight Charts 활용:
- 수익률 곡선: Line Chart
- 드로우다운: Area Chart
- 월별 히트맵: Custom Heatmap (Tailwind grid)

---

## 6. Task 4-4: 시장 상태 분석

### 6.1 목표
- KOSPI/KOSDAQ 지수 상태 분석
- 섹터별 강세/약세 분석
- 시장 전반 투자 심리 지표

### 6.2 분석 지표

```python
@dataclass
class MarketState:
    """시장 상태"""
    index_code: str  # "KOSPI" or "KOSDAQ"
    current_price: float
    change_pct: float
    
    # 기술적 지표
    rsi_14: float
    ma_5: float
    ma_20: float
    ma_60: float
    trend: Literal["UPTREND", "DOWNTREND", "SIDEWAYS"]
    
    # 투자 심리
    fear_greed_index: float  # 0-100 (0=극도의 공포, 100=극도의 탐욕)
    volume_ratio: float      # 평균 대비 거래량
    
    # 섹터 분석
    top_sectors: list[SectorPerformance]
    bottom_sectors: list[SectorPerformance]
```

### 6.3 API 엔드포인트

```
GET /api/v1/analysis/market
  - Response: {
      "kospi": MarketState,
      "kosdaq": MarketState,
      "recommendation": "현재 시장은 과매도 구간으로..."
    }

GET /api/v1/analysis/sectors
  - Response: list of SectorPerformance
```

---

## 7. Task 4-5: AI 추천 종목

### 7.1 목표
- BNF 전략 기반 종목 스코어링
- 매수/매도 추천 목록
- 추천 근거 설명

### 7.2 스코어링 로직

```python
@dataclass
class StockRecommendation:
    """종목 추천"""
    stock_code: str
    stock_name: str
    current_price: float
    
    score: float  # 0-100
    signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    
    # 지표별 점수
    rsi_score: float
    macd_score: float
    volume_score: float
    trend_score: float
    
    # 추천 근거
    reasons: list[str]


class AIRecommender:
    """AI 종목 추천"""
    
    async def get_recommendations(
        self,
        top_n: int = 10,
    ) -> list[StockRecommendation]:
        """상위 N개 매수 추천 종목"""
    
    async def score_stock(
        self,
        stock_code: str,
    ) -> StockRecommendation:
        """단일 종목 스코어링"""
```

### 7.3 API 엔드포인트

```
GET /api/v1/analysis/recommend
  - Query: top_n=10
  - Response: list of StockRecommendation

GET /api/v1/analysis/signals
  - Response: 현재 활성 신호 목록
```

---

## 8. Task 4-6: 신호 강도 시각화

### 8.1 목표
- 신호 발생 시 강도 게이지 표시
- 히스토리 신호 차트
- 지표별 기여도 시각화

### 8.2 UI 컴포넌트

```typescript
// frontend/components/analysis/SignalStrengthGauge.tsx

interface SignalStrengthGaugeProps {
  strength: number;  // 0-100
  signal: "BUY" | "SELL" | "HOLD";
}

export function SignalStrengthGauge({ strength, signal }: SignalStrengthGaugeProps) {
  // 반원형 게이지
  // 색상: BUY=초록, SELL=빨강, HOLD=노랑
}


// frontend/components/analysis/IndicatorContribution.tsx

interface IndicatorContributionProps {
  contributions: {
    indicator: string;
    score: number;
    weight: number;
  }[];
}

export function IndicatorContribution({ contributions }: IndicatorContributionProps) {
  // 수평 바 차트 (각 지표의 기여도)
}
```

---

## 9. 데이터 모델

### 9.1 신규 테이블

```sql
-- stock_prices: 주가 일봉 데이터
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(12, 2) NOT NULL,
    high_price NUMERIC(12, 2) NOT NULL,
    low_price NUMERIC(12, 2) NOT NULL,
    close_price NUMERIC(12, 2) NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_code, trade_date)
);

CREATE INDEX ix_stock_prices_code_date ON stock_prices(stock_code, trade_date);

-- backtest_results: 백테스트 결과 저장
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(100),
    config JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- backtest_trades: 백테스트 거래 기록
CREATE TABLE backtest_trades (
    id SERIAL PRIMARY KEY,
    backtest_id UUID REFERENCES backtest_results(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    commission NUMERIC(10, 2) NOT NULL,
    tax NUMERIC(10, 2) NOT NULL,
    signal_reason TEXT
);
```

### 9.2 마이그레이션 파일

```python
# backend/alembic/versions/xxxx_add_backtest_tables.py

def upgrade():
    op.create_table("stock_prices", ...)
    op.create_table("backtest_results", ...)
    op.create_table("backtest_trades", ...)

def downgrade():
    op.drop_table("backtest_trades")
    op.drop_table("backtest_results")
    op.drop_table("stock_prices")
```

---

## 10. API 설계

### 10.1 백테스팅 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/backtest/prices/sync | 주가 데이터 동기화 |
| GET | /api/v1/backtest/prices/{code} | 주가 조회 |
| POST | /api/v1/backtest/run | 백테스트 실행 |
| GET | /api/v1/backtest/results | 결과 목록 |
| GET | /api/v1/backtest/results/{id} | 결과 상세 |
| DELETE | /api/v1/backtest/results/{id} | 결과 삭제 |

### 10.2 분석 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/analysis/market | 시장 상태 |
| GET | /api/v1/analysis/sectors | 섹터별 분석 |
| GET | /api/v1/analysis/recommend | AI 추천 종목 |
| GET | /api/v1/analysis/signals | 현재 신호 목록 |
| GET | /api/v1/analysis/signals/{code} | 종목별 신호 |

---

## 검증 체크리스트

### Task 4-1: 과거 데이터 수집
- [ ] StockPrice 모델 생성 및 마이그레이션
- [ ] PriceHistoryService 구현
- [ ] KIS API 일봉 데이터 수집 연동
- [ ] 증분 동기화 동작 확인
- [ ] API 엔드포인트 테스트

### Task 4-2: 백테스팅 엔진
- [ ] BacktestEngine 클래스 구현
- [ ] 거래 비용 (수수료, 세금) 반영
- [ ] 손절/익절 로직 동작
- [ ] 일별 자산 추적
- [ ] 결과 지표 계산 정확성

### Task 4-3: 결과 리포트
- [ ] MetricsCards 컴포넌트
- [ ] EquityCurveChart 컴포넌트
- [ ] TradesTable 컴포넌트
- [ ] DrawdownChart 컴포넌트
- [ ] 백테스트 결과 페이지 통합

### Task 4-4: 시장 상태 분석
- [ ] KOSPI/KOSDAQ 지수 분석
- [ ] 섹터 분석 API
- [ ] 시장 상태 페이지 UI

### Task 4-5: AI 추천 종목
- [ ] 스코어링 로직 구현
- [ ] 추천 API
- [ ] 추천 목록 UI

### Task 4-6: 신호 강도 시각화
- [ ] SignalStrengthGauge 컴포넌트
- [ ] IndicatorContribution 컴포넌트
- [ ] Analysis 페이지 통합
