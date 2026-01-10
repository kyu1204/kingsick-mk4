# Task 3-2: AI 자동 스캔 (Stock Scanner) 설계

> **작성일**: 2026-01-10
> **상태**: 설계 완료
> **우선순위**: P3

## 개요

사용자가 직접 종목을 지정하지 않아도 AI가 자동으로 매매 대상 종목을 스캔하는 기능.
기존 BNF 전략과 SignalGenerator를 활용하여 전체 시장에서 매매 신호가 강한 종목을 찾아낸다.

## 기능 요구사항

### 핵심 기능
1. **시장 스캔**: KOSPI/KOSDAQ 전체 또는 특정 섹터 종목 스캔
2. **신호 필터링**: BNF 전략 기준 confidence 임계값 이상 종목만 반환
3. **정렬**: confidence 높은 순으로 정렬
4. **결과 제한**: 상위 N개 종목만 반환 (기본 10개)

### 스캔 조건
- **BUY 스캔**: RSI < 30 + 거래량 급증 + 볼린저밴드 하단 이탈
- **SELL 스캔**: RSI > 70 + 거래량 감소 + 볼린저밴드 상단 이탈
- **최소 신뢰도**: 0.5 이상 (50%)

## 아키텍처

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Scanner API    │────▶│  StockScanner    │────▶│  KIS API        │
│  /api/v1/scan   │     │  Service         │     │  (가격/거래량)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  SignalGenerator │
                        │  + BNFStrategy   │
                        └──────────────────┘
```

## Backend 구현

### 1. StockScanner 서비스

```python
# backend/app/services/stock_scanner.py

@dataclass
class ScanResult:
    stock_code: str
    stock_name: str
    signal: str  # "BUY" or "SELL"
    confidence: float
    current_price: float
    rsi: float
    volume_spike: bool
    reasoning: list[str]

class StockScanner:
    def __init__(
        self,
        kis_api: KISApiClient,
        signal_generator: SignalGenerator,
    ) -> None: ...
    
    async def scan_market(
        self,
        scan_type: str = "BUY",  # "BUY" or "SELL"
        min_confidence: float = 0.5,
        limit: int = 10,
        sector: str | None = None,
    ) -> list[ScanResult]: ...
    
    async def get_stock_universe(
        self,
        sector: str | None = None,
    ) -> list[dict]: ...
```

### 2. Scanner API 라우터

```python
# backend/app/api/scanner.py

@router.get("/scan")
async def scan_stocks(
    scan_type: str = Query("BUY", enum=["BUY", "SELL"]),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    sector: str | None = Query(None),
    current_user: User = Depends(get_current_user),
) -> ScanResponse: ...

@router.get("/scan/sectors")
async def get_sectors() -> list[str]: ...
```

### 3. 종목 유니버스

초기 버전에서는 하드코딩된 대표 종목 리스트 사용:
- KOSPI 대형주 30개
- KOSDAQ 우량주 20개

추후 KIS API의 전체 종목 조회 API 연동 가능.

## Frontend 구현

### Analysis 페이지에 Scanner 탭 추가

```tsx
// app/analysis/page.tsx

<Tabs defaultValue="scanner">
  <TabsTrigger value="scanner">AI 스캐너</TabsTrigger>
  <TabsTrigger value="signals">신호 분석</TabsTrigger>
</Tabs>

<TabsContent value="scanner">
  <ScannerPanel />
</TabsContent>
```

### ScannerPanel 컴포넌트

- 스캔 타입 선택 (BUY/SELL)
- 최소 신뢰도 슬라이더 (0.5 ~ 1.0)
- 결과 개수 설정 (10, 20, 30)
- 스캔 버튼
- 결과 테이블 (종목명, 현재가, 신뢰도, RSI, 추가 버튼)

## API 응답 형식

```json
{
  "results": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "signal": "BUY",
      "confidence": 0.78,
      "current_price": 72500,
      "rsi": 25.3,
      "volume_spike": true,
      "reasoning": ["RSI 과매도 (25.3)", "거래량 급증", "볼린저 하단 이탈"]
    }
  ],
  "total": 1,
  "scan_type": "BUY",
  "scanned_at": "2026-01-10T15:30:00Z"
}
```

## 테스트 계획

### Unit Tests
- `test_stock_scanner.py`
  - `test_scan_returns_buy_signals`
  - `test_scan_returns_sell_signals`
  - `test_scan_filters_by_confidence`
  - `test_scan_limits_results`
  - `test_scan_empty_universe`

### Integration Tests
- `test_api_scanner.py`
  - `test_scan_endpoint_success`
  - `test_scan_endpoint_unauthorized`
  - `test_sectors_endpoint`

## 구현 순서

1. ✅ 설계 문서 작성
2. ⏳ Unit 테스트 먼저 작성 (TDD)
3. ⏳ StockScanner 서비스 구현
4. ⏳ Scanner API 라우터 구현
5. ⏳ Integration 테스트 작성
6. ⏳ Frontend ScannerPanel 구현
7. ⏳ 브라우저 테스트

## 참고사항

- KIS API 호출 제한을 고려하여 병렬 요청 수 제한 (동시 5개)
- 스캔 결과는 캐싱하지 않음 (항상 최신 데이터)
- 종목 유니버스는 하드코딩으로 시작, 추후 DB 또는 외부 API 연동
