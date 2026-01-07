# KingSick - AI 기반 BNF 스타일 자동매매 시스템 설계서

> 작성일: 2026-01-07
> 버전: 1.0

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [기술 스택 & 아키텍처](#2-기술-스택--아키텍처)
3. [핵심 기능 상세 설계](#3-핵심-기능-상세-설계)
4. [데이터 모델 & API 설계](#4-데이터-모델--api-설계)
5. [개발 로드맵 & 폴더 구조](#5-개발-로드맵--폴더-구조)
6. [TDD 전략](#6-tdd-전략)
7. [보안 & 배포 전략](#7-보안--배포-전략)

---

## 1. 시스템 개요

### 1.1 프로젝트명
**KingSick** - AI 기반 BNF 스타일 자동매매 시스템

### 1.2 핵심 컨셉

```
┌─────────────────────────────────────────────────────┐
│                    KingSick                         │
├─────────────────────────────────────────────────────┤
│  🎯 목표: BNF 전략 + AI = 자동화된 스윙 트레이딩    │
│  👥 사용자: 소규모 그룹 (5명 이내)                  │
│  📊 시장: 국내 코스피 (한국투자증권 API)            │
│  🖥️ 플랫폼: 웹 어플리케이션                        │
└─────────────────────────────────────────────────────┘
```

### 1.3 핵심 기능 요약

| 기능 | 모드 |
|------|------|
| 매매 실행 | 🤖 자동 / 👀 알림형 선택 |
| 종목 선정 | 📌 직접 지정 / 🔍 AI 스캔 (옵션) |
| 리스크 관리 | 사용자 설정 + AI 추천 + 트레일링(옵션) |
| 알림 | 텔레그램 / 슬랙 |

### 1.4 BNF 전략 기반

**BNF (타카시 코테가와)** - 일본의 전설적인 개인 트레이더

| 항목 | 내용 |
|------|------|
| 본명 | 코테가와 타카시 (小手川隆) |
| 시작 자금 | 약 160만 엔 (~1,500만 원) |
| 성과 | 수년 만에 수백억 엔 달성 |
| 스타일 | 스윙 + 데이트레이딩 혼합 |

**BNF 핵심 전략:**
- 기술적 분석 중심 (이동평균선, 거래량 등)
- 과매도/과매수 구간 포착 → 역추세 매매
- 철저한 손절매 규칙
- 감정 배제, 기계적 트레이딩

---

## 2. 기술 스택 & 아키텍처

### 2.1 기술 스택

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
├─────────────────────────────────────────────────────┤
│  Next.js 14 (React)                                 │
│  - TypeScript                                       │
│  - TailwindCSS + shadcn/ui                          │
│  - TradingView 차트 라이브러리 (Lightweight Charts) │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                    Backend                          │
├─────────────────────────────────────────────────────┤
│  Python FastAPI                                     │
│  - 한국투자증권 API 연동 (PyKis)                    │
│  - AI/ML: scikit-learn, PyTorch                    │
│  - 기술적 분석: TA-Lib, pandas-ta                   │
│  - 스케줄러: APScheduler (자동매매 루프)            │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                    Database                         │
├─────────────────────────────────────────────────────┤
│  PostgreSQL - 사용자, 매매내역, 설정                │
│  Redis - 실시간 시세 캐시, 세션                     │
│  TimescaleDB - 시계열 데이터 (백테스팅용)           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                  External APIs                      │
├─────────────────────────────────────────────────────┤
│  한국투자증권 REST API - 시세, 주문, 잔고           │
│  Telegram Bot API - 알림 발송                       │
│  Slack Webhook - 알림 발송                          │
└─────────────────────────────────────────────────────┘
```

### 2.2 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                         사용자                                │
│                    (웹 브라우저)                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │대시보드  │ │종목관리 │ │설정    │ │AI분석   │            │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Trading Engine                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │ │
│  │  │ 시세수신  │ │ AI 분석  │ │ 주문실행  │ │ 리스크    │ │ │
│  │  │ Service  │ │ Service  │ │ Service  │ │ Manager   │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Alert Service                        │ │
│  │  Telegram Bot │ Slack Webhook                         │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────┐
    │PostgreSQL│    │  Redis   │    │한국투자증권   │
    │          │    │          │    │   REST API   │
    └──────────┘    └──────────┘    └──────────────┘
```

---

## 3. 핵심 기능 상세 설계

### 3.1 듀얼 매매 모드

```
┌─────────────────────────────────────────────────────────────┐
│                    Trading Mode Controller                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐         ┌─────────────────┐          │
│   │   🤖 AUTO MODE  │         │  👀 ALERT MODE  │          │
│   ├─────────────────┤         ├─────────────────┤          │
│   │ AI 신호 발생    │         │ AI 신호 발생    │          │
│   │      ↓         │         │      ↓          │          │
│   │ 리스크 체크     │         │ 메신저 알림     │          │
│   │      ↓         │         │      ↓          │          │
│   │ 자동 주문 실행  │         │ 사용자 승인 대기 │          │
│   │      ↓         │         │      ↓          │          │
│   │ 체결 알림 발송  │         │ 승인 시 주문    │          │
│   └─────────────────┘         └─────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**AUTO MODE 플로우:**
```
1. 스케줄러가 매 1분마다 실행
2. 보유 종목 + 관심 종목 시세 수신
3. 기술적 지표 계산 (MA, RSI, 볼린저밴드 등)
4. AI 모델이 매수/매도 신호 판단
5. 신호 발생 시 → 리스크 체크 (손절/익절/자금)
6. 통과 시 → 한국투자증권 API로 주문
7. 체결 결과 → DB 저장 + 메신저 알림
```

**ALERT MODE 플로우:**
```
1~4. AUTO와 동일
5. 신호 발생 시 → 메신저로 알림 발송
   "[매수 신호] 삼성전자 / 현재가 72,000 / RSI 28 / AI 확신도 85%"
6. 사용자가 텔레그램에서 "승인" 버튼 클릭
7. 승인 시 → 주문 실행
```

### 3.2 AI 매매 판단 로직

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Signal Generator                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Input Layer (기술적 지표)                                 │
│   ┌─────┬─────┬─────┬─────┬─────┬─────┐                   │
│   │ MA  │ RSI │ MACD│ 볼린저│거래량│ 기타│                   │
│   └──┬──┴──┬──┴──┬──┴──┬──┴──┬──┴──┬──┘                   │
│      └─────┴─────┴─────┴─────┴─────┘                       │
│                      ↓                                      │
│   ┌─────────────────────────────────────┐                  │
│   │         AI/ML 모델                  │                  │
│   │  - 과매도/과매수 패턴 인식          │                  │
│   │  - BNF 스타일 역추세 매매 학습       │                  │
│   │  - 최적 진입/청산 타이밍 예측       │                  │
│   └─────────────────────────────────────┘                  │
│                      ↓                                      │
│   Output Layer                                              │
│   ┌─────────────────────────────────────┐                  │
│   │ signal: BUY / SELL / HOLD           │                  │
│   │ confidence: 0.0 ~ 1.0               │                  │
│   │ reason: "RSI 25, 볼린저 하단 이탈"  │                  │
│   └─────────────────────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**BNF 스타일 핵심 규칙:**

| 조건 | 신호 |
|------|------|
| RSI < 30 + 거래량 급증 + 볼린저 하단 이탈 | 매수 검토 |
| RSI > 70 + 거래량 감소 + 볼린저 상단 이탈 | 매도 검토 |
| 5일선 > 20일선 골든크로스 | 추세 상승 확인 |
| 손절/익절 라인 도달 | 즉시 청산 |

### 3.3 리스크 관리 시스템

```
┌─────────────────────────────────────────────────────────────┐
│                    Risk Manager                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   사용자 설정값                    AI 추천                  │
│   ┌──────────────────┐            ┌──────────────────┐     │
│   │ 손절: -5%        │     💡     │ "변동성 높음,    │     │
│   │ 익절: +10%       │  ◄─────►   │  -3%로 조정 권장"│     │
│   │ 최대 투자금: 100만│            └──────────────────┘     │
│   │ 트레일링: OFF    │                                      │
│   └──────────────────┘                                      │
│                                                             │
│   체크 항목:                                                │
│   ☑️ 손절 라인 도달 여부                                    │
│   ☑️ 익절 라인 도달 여부                                    │
│   ☑️ 트레일링 스탑 조건 (ON일 경우)                         │
│   ☑️ 최대 투자금 한도                                       │
│   ☑️ 동시 보유 종목 수 제한                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 트레일링 스탑

```
예시: 10,000원에 매수, 트레일링 스탑 -5% 설정

주가 흐름:
10,000원 → 손절선: 9,500원 (-5%)
   ↓ 상승
11,000원 → 손절선: 10,450원 (자동 상향!)
   ↓ 상승
12,000원 → 손절선: 11,400원 (자동 상향!)
   ↓ 하락
11,400원 도달 → 자동 매도! (수익 +14% 확보)
```

### 3.5 종목 선정 듀얼 모드

```
┌─────────────────────────────────────────┐
│            종목 선정 모드                │
├──────────────────┬──────────────────────┤
│   🔍 AI 스캔     │   📌 직접 지정        │
│  (옵셔널 ON/OFF) │  (가치투자 종목)      │
└──────────────────┴──────────────────────┘
```

---

## 4. 데이터 모델 & API 설계

### 4.1 데이터베이스 스키마

```sql
-- 사용자 테이블
┌─────────────────────────────────────────────┐
│                   users                     │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ email           │ VARCHAR (unique)          │
│ name            │ VARCHAR                   │
│ kis_app_key     │ VARCHAR (암호화)          │
│ kis_app_secret  │ VARCHAR (암호화)          │
│ kis_account_no  │ VARCHAR (암호화)          │
│ created_at      │ TIMESTAMP                 │
└─────────────────────────────────────────────┘

-- 종목 관심 리스트
┌─────────────────────────────────────────────┐
│                 watchlist                   │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ user_id         │ UUID (FK → users)         │
│ stock_code      │ VARCHAR (종목코드)        │
│ stock_name      │ VARCHAR                   │
│ is_ai_scan      │ BOOLEAN (AI발굴 여부)     │
│ created_at      │ TIMESTAMP                 │
└─────────────────────────────────────────────┘

-- 매매 설정
┌─────────────────────────────────────────────┐
│              trading_settings               │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ user_id         │ UUID (FK → users)         │
│ mode            │ ENUM (auto/alert)         │
│ stop_loss       │ DECIMAL (손절 %)          │
│ take_profit     │ DECIMAL (익절 %)          │
│ trailing_stop   │ BOOLEAN                   │
│ trailing_pct    │ DECIMAL (트레일링 %)      │
│ max_investment  │ DECIMAL (최대 투자금)     │
│ max_stocks      │ INTEGER (최대 종목수)     │
│ indicators      │ JSONB (사용할 지표들)     │
└─────────────────────────────────────────────┘

-- 매매 내역
┌─────────────────────────────────────────────┐
│                  trades                     │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ user_id         │ UUID (FK → users)         │
│ stock_code      │ VARCHAR                   │
│ stock_name      │ VARCHAR                   │
│ side            │ ENUM (buy/sell)           │
│ quantity        │ INTEGER                   │
│ price           │ DECIMAL                   │
│ total_amount    │ DECIMAL                   │
│ signal_reason   │ TEXT (AI 판단 근거)       │
│ confidence      │ DECIMAL (AI 확신도)       │
│ status          │ ENUM (pending/filled/failed)│
│ executed_at     │ TIMESTAMP                 │
└─────────────────────────────────────────────┘

-- 포지션 (현재 보유)
┌─────────────────────────────────────────────┐
│                 positions                   │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ user_id         │ UUID (FK → users)         │
│ stock_code      │ VARCHAR                   │
│ stock_name      │ VARCHAR                   │
│ quantity        │ INTEGER                   │
│ avg_price       │ DECIMAL (평균 단가)       │
│ current_price   │ DECIMAL (현재가)          │
│ profit_pct      │ DECIMAL (수익률)          │
│ highest_price   │ DECIMAL (트레일링용 최고가)│
│ updated_at      │ TIMESTAMP                 │
└─────────────────────────────────────────────┘

-- 알림 설정
┌─────────────────────────────────────────────┐
│             alert_settings                  │
├─────────────────────────────────────────────┤
│ id              │ UUID (PK)                 │
│ user_id         │ UUID (FK → users)         │
│ telegram_chat_id│ VARCHAR                   │
│ slack_webhook   │ VARCHAR                   │
│ enabled         │ BOOLEAN                   │
└─────────────────────────────────────────────┘
```

### 4.2 REST API 설계

```yaml
# 인증
POST   /api/auth/login          # 로그인
POST   /api/auth/register       # 회원가입
POST   /api/auth/logout         # 로그아웃

# 사용자 설정
GET    /api/settings            # 설정 조회
PUT    /api/settings            # 설정 수정
PUT    /api/settings/kis        # 한국투자증권 API 키 설정
PUT    /api/settings/alerts     # 알림 설정

# 매매 모드
GET    /api/trading/mode        # 현재 모드 조회
PUT    /api/trading/mode        # 모드 변경 (auto/alert)
POST   /api/trading/start       # 자동매매 시작
POST   /api/trading/stop        # 자동매매 중지

# 종목 관리
GET    /api/watchlist           # 관심종목 조회
POST   /api/watchlist           # 관심종목 추가
DELETE /api/watchlist/:id       # 관심종목 삭제
POST   /api/watchlist/ai-scan   # AI 종목 스캔 실행

# 포지션 & 거래
GET    /api/positions           # 보유종목 조회
GET    /api/trades              # 매매내역 조회
GET    /api/trades/:id          # 매매 상세 (AI 판단 근거 포함)
POST   /api/trades/approve/:id  # 알림모드 - 매매 승인

# 대시보드
GET    /api/dashboard/summary   # 요약 (총 수익률, 보유종목 수 등)
GET    /api/dashboard/profit    # 수익률 차트 데이터
GET    /api/dashboard/stats     # 통계 (승률, 평균수익 등)

# AI 분석 (Phase 4)
GET    /api/analysis/market     # 시장 상태 분석
GET    /api/analysis/recommend  # AI 추천 종목
GET    /api/analysis/signals    # 현재 신호 목록

# 백테스팅 (Phase 4)
POST   /api/backtest/run        # 백테스트 실행
GET    /api/backtest/results    # 백테스트 결과 조회
```

### 4.3 실시간 데이터 (WebSocket)

```
┌─────────────────────────────────────────────┐
│              WebSocket Events               │
├─────────────────────────────────────────────┤
│                                             │
│  Server → Client                            │
│  ─────────────────                          │
│  • price_update    : 실시간 시세 업데이트   │
│  • signal_alert    : AI 매매 신호 발생      │
│  • trade_executed  : 주문 체결 알림         │
│  • position_update : 보유종목 변동          │
│                                             │
│  Client → Server                            │
│  ─────────────────                          │
│  • subscribe       : 종목 시세 구독         │
│  • unsubscribe     : 종목 시세 구독 해제    │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 5. 개발 로드맵 & 폴더 구조

### 5.1 개발 로드맵

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: 핵심 자동매매                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 프로젝트 초기 설정                                      │
│     └─ Next.js + FastAPI + PostgreSQL + Redis 환경 구성     │
│                                                             │
│  ✅ 한국투자증권 API 연동                                   │
│     ├─ 인증 (OAuth)                                         │
│     ├─ 시세 조회                                            │
│     ├─ 주문 실행                                            │
│     └─ 잔고 조회                                            │
│                                                             │
│  ✅ 기술적 지표 엔진 (H)                                    │
│     ├─ MA, RSI, MACD, 볼린저밴드, 거래량                    │
│     └─ 지표 선택 기능                                       │
│                                                             │
│  ✅ AI 매매 신호 생성기                                     │
│     ├─ BNF 스타일 규칙 기반 모델                            │
│     └─ 과매도/과매수 패턴 인식                              │
│                                                             │
│  ✅ 듀얼 매매 모드 (A)                                      │
│     ├─ AUTO 모드: 자동 주문 실행                            │
│     └─ ALERT 모드: 신호만 발생                              │
│                                                             │
│  ✅ 리스크 관리 (C)                                         │
│     ├─ 손절/익절 설정                                       │
│     ├─ AI 추천                                              │
│     └─ 트레일링 스탑 (옵션)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Phase 2: 모니터링                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 대시보드 (F)                                            │
│     ├─ 수익률 현황 (일별/월별/누적 차트)                    │
│     ├─ 보유 종목 현황                                       │
│     └─ 매매 내역 + AI 판단 근거                             │
│                                                             │
│  ✅ 사용자 인증                                             │
│     ├─ 로그인/회원가입                                      │
│     └─ 개인별 API 키 관리                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Phase 3: 확장                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 종목 관리 (B)                                           │
│     ├─ 직접 지정                                            │
│     └─ AI 자동 스캔 (옵션)                                  │
│                                                             │
│  ✅ 메신저 알림 (D)                                         │
│     ├─ Telegram Bot 연동                                    │
│     ├─ Slack Webhook 연동                                   │
│     └─ 알림 승인 → 주문 실행 연결                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Phase 4: 고도화                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 백테스팅 (E)                                            │
│     ├─ 과거 데이터 수집 및 저장                             │
│     ├─ 전략 시뮬레이션 엔진                                 │
│     └─ 결과 리포트 (수익률, MDD, 샤프비율 등)               │
│                                                             │
│  ✅ AI 분석 페이지 (G)                                      │
│     ├─ 시장 상태 분석                                       │
│     ├─ AI 추천 종목                                         │
│     └─ 신호 강도 시각화                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 프로젝트 폴더 구조

```
kingsick/
├── frontend/                     # Next.js 프론트엔드
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/
│   │   │   ├── page.tsx          # 메인 대시보드
│   │   │   ├── positions/        # 보유종목
│   │   │   └── trades/           # 매매내역
│   │   ├── watchlist/            # 종목 관리
│   │   ├── analysis/             # AI 분석 (Phase 4)
│   │   ├── backtest/             # 백테스팅 (Phase 4)
│   │   ├── settings/             # 설정
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                   # shadcn/ui 컴포넌트
│   │   ├── charts/               # 차트 컴포넌트
│   │   ├── trading/              # 매매 관련 컴포넌트
│   │   └── layout/               # 레이아웃 컴포넌트
│   ├── lib/
│   │   ├── api.ts                # API 클라이언트
│   │   └── websocket.ts          # WebSocket 클라이언트
│   └── package.json
│
├── backend/                      # Python FastAPI 백엔드
│   ├── app/
│   │   ├── main.py               # FastAPI 앱 진입점
│   │   ├── config.py             # 환경설정
│   │   ├── database.py           # DB 연결
│   │   │
│   │   ├── api/                  # API 라우터
│   │   │   ├── auth.py
│   │   │   ├── trading.py
│   │   │   ├── watchlist.py
│   │   │   ├── positions.py
│   │   │   ├── dashboard.py
│   │   │   └── settings.py
│   │   │
│   │   ├── models/               # SQLAlchemy 모델
│   │   │   ├── user.py
│   │   │   ├── trade.py
│   │   │   ├── position.py
│   │   │   └── settings.py
│   │   │
│   │   ├── services/             # 비즈니스 로직
│   │   │   ├── kis_api.py        # 한국투자증권 API
│   │   │   ├── trading_engine.py # 자동매매 엔진
│   │   │   ├── signal_generator.py # AI 신호 생성
│   │   │   ├── risk_manager.py   # 리스크 관리
│   │   │   ├── indicator.py      # 기술적 지표
│   │   │   └── alert.py          # 알림 서비스
│   │   │
│   │   ├── ai/                   # AI/ML 모델
│   │   │   ├── bnf_strategy.py   # BNF 전략 모델
│   │   │   ├── pattern_detector.py # 패턴 인식
│   │   │   └── trainer.py        # 모델 학습
│   │   │
│   │   └── scheduler/            # 스케줄러
│   │       └── trading_loop.py   # 자동매매 루프
│   │
│   ├── tests/                    # 테스트
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml            # Docker 구성
├── .env.example                  # 환경변수 예시
└── README.md
```

---

## 6. TDD 전략

### 6.1 TDD 사이클

```
┌─────────────────────────────────────────────────────────────┐
│                    TDD 사이클                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│         🔴 RED          🟢 GREEN         🔵 REFACTOR        │
│      ┌─────────┐      ┌─────────┐      ┌─────────┐         │
│      │테스트   │ ───► │최소한의 │ ───► │코드     │         │
│      │먼저 작성│      │구현     │      │개선     │         │
│      │(실패)   │      │(통과)   │      │(리팩토링)│         │
│      └─────────┘      └─────────┘      └─────────┘         │
│           ▲                                   │             │
│           └───────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 테스트 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Pyramid                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        ▲                                    │
│                       /  \        E2E Tests (10%)           │
│                      /    \       - Playwright              │
│                     /──────\      - 전체 플로우 검증        │
│                    /        \                               │
│                   /          \    Integration Tests (30%)   │
│                  /────────────\   - API 엔드포인트          │
│                 /              \  - DB 연동                 │
│                /                \ - 외부 API Mock           │
│               /──────────────────\                          │
│              /                    \ Unit Tests (60%)        │
│             /______________________\- 개별 함수/클래스      │
│                                     - 비즈니스 로직         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 테스트 폴더 구조

```
kingsick/
├── backend/
│   ├── tests/
│   │   ├── conftest.py              # pytest fixtures
│   │   │
│   │   ├── unit/                    # 단위 테스트 (60%)
│   │   │   ├── test_indicator.py    # 기술적 지표 계산
│   │   │   ├── test_signal.py       # AI 신호 생성
│   │   │   ├── test_risk_manager.py # 리스크 관리 로직
│   │   │   ├── test_bnf_strategy.py # BNF 전략 규칙
│   │   │   └── test_trailing_stop.py# 트레일링 스탑 계산
│   │   │
│   │   ├── integration/             # 통합 테스트 (30%)
│   │   │   ├── test_kis_api.py      # 한국투자증권 API (Mock)
│   │   │   ├── test_trading_engine.py # 매매 엔진 통합
│   │   │   ├── test_api_endpoints.py  # REST API 테스트
│   │   │   └── test_websocket.py    # WebSocket 테스트
│   │   │
│   │   ├── e2e/                     # E2E 테스트 (10%)
│   │   │   ├── test_auto_trading.py # 자동매매 전체 플로우
│   │   │   └── test_alert_mode.py   # 알림모드 전체 플로우
│   │   │
│   │   └── fixtures/                # 테스트 데이터
│   │       ├── mock_kis_responses.py
│   │       └── sample_stock_data.py
│   │
│   ├── pytest.ini
│   └── .coveragerc                  # 커버리지 설정
│
├── frontend/
│   ├── __tests__/
│   │   ├── components/              # 컴포넌트 테스트
│   │   │   ├── Dashboard.test.tsx
│   │   │   ├── TradeList.test.tsx
│   │   │   └── Chart.test.tsx
│   │   │
│   │   ├── hooks/                   # 커스텀 훅 테스트
│   │   │   └── useWebSocket.test.ts
│   │   │
│   │   └── e2e/                     # Playwright E2E
│   │       ├── trading-flow.spec.ts
│   │       └── dashboard.spec.ts
│   │
│   ├── jest.config.js
│   └── playwright.config.ts
```

### 6.4 핵심 테스트 케이스

```python
# ═══════════════════════════════════════════════════════════
# Unit Tests - 기술적 지표
# ═══════════════════════════════════════════════════════════

class TestIndicator:
    """기술적 지표 계산 테스트"""

    def test_rsi_oversold_detection(self):
        """RSI 30 이하 = 과매도 감지"""

    def test_rsi_overbought_detection(self):
        """RSI 70 이상 = 과매수 감지"""

    def test_bollinger_band_breakout(self):
        """볼린저밴드 이탈 감지"""

    def test_moving_average_crossover(self):
        """이동평균 골든/데드 크로스 감지"""

    def test_volume_spike_detection(self):
        """거래량 급증 감지"""


# ═══════════════════════════════════════════════════════════
# Unit Tests - AI 신호 생성
# ═══════════════════════════════════════════════════════════

class TestSignalGenerator:
    """AI 매매 신호 생성 테스트"""

    def test_buy_signal_on_oversold(self):
        """과매도 조건 충족 시 매수 신호"""

    def test_sell_signal_on_overbought(self):
        """과매수 조건 충족 시 매도 신호"""

    def test_hold_signal_on_neutral(self):
        """중립 상태에서 HOLD 신호"""

    def test_confidence_score_calculation(self):
        """신호 확신도 계산 정확성"""

    def test_signal_reason_generation(self):
        """신호 발생 근거 텍스트 생성"""


# ═══════════════════════════════════════════════════════════
# Unit Tests - 리스크 관리
# ═══════════════════════════════════════════════════════════

class TestRiskManager:
    """리스크 관리 로직 테스트"""

    def test_stop_loss_trigger(self):
        """-5% 도달 시 손절 트리거"""

    def test_take_profit_trigger(self):
        """+10% 도달 시 익절 트리거"""

    def test_trailing_stop_adjustment(self):
        """가격 상승 시 트레일링 스탑 상향 조정"""

    def test_trailing_stop_trigger(self):
        """최고점 대비 하락 시 트레일링 스탑 트리거"""

    def test_max_investment_limit(self):
        """최대 투자금 한도 초과 방지"""

    def test_max_stocks_limit(self):
        """최대 보유 종목 수 제한"""


# ═══════════════════════════════════════════════════════════
# Integration Tests - 매매 엔진
# ═══════════════════════════════════════════════════════════

class TestTradingEngine:
    """매매 엔진 통합 테스트"""

    def test_auto_mode_full_cycle(self):
        """AUTO 모드: 신호 → 주문 → 체결 전체 사이클"""

    def test_alert_mode_notification(self):
        """ALERT 모드: 신호 → 알림 발송"""

    def test_alert_mode_approval_execution(self):
        """ALERT 모드: 승인 → 주문 실행"""

    def test_mode_switching(self):
        """AUTO ↔ ALERT 모드 전환"""


# ═══════════════════════════════════════════════════════════
# Integration Tests - 한국투자증권 API (Mock)
# ═══════════════════════════════════════════════════════════

class TestKisAPI:
    """한국투자증권 API 연동 테스트 (Mock)"""

    def test_authentication(self):
        """OAuth 인증 성공"""

    def test_get_stock_price(self):
        """현재가 조회"""

    def test_place_buy_order(self):
        """매수 주문 실행"""

    def test_place_sell_order(self):
        """매도 주문 실행"""

    def test_get_balance(self):
        """잔고 조회"""

    def test_api_error_handling(self):
        """API 오류 처리"""
```

### 6.5 TDD 개발 예시

```python
# ═══════════════════════════════════════════════════════════
# Step 1: 🔴 RED - 실패하는 테스트 먼저 작성
# ═══════════════════════════════════════════════════════════

# tests/unit/test_trailing_stop.py
def test_trailing_stop_updates_on_price_increase():
    """가격 상승 시 트레일링 스탑 라인이 따라 올라가야 함"""
    # Given
    trailing = TrailingStop(
        entry_price=10000,
        trailing_pct=5.0  # -5%
    )

    # When
    trailing.update_price(11000)  # 가격 10% 상승

    # Then
    assert trailing.stop_price == 10450  # 11000 * 0.95
    assert trailing.highest_price == 11000


# ═══════════════════════════════════════════════════════════
# Step 2: 🟢 GREEN - 테스트 통과하는 최소 구현
# ═══════════════════════════════════════════════════════════

# app/services/risk_manager.py
class TrailingStop:
    def __init__(self, entry_price: float, trailing_pct: float):
        self.entry_price = entry_price
        self.trailing_pct = trailing_pct
        self.highest_price = entry_price
        self.stop_price = entry_price * (1 - trailing_pct / 100)

    def update_price(self, current_price: float):
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.stop_price = current_price * (1 - self.trailing_pct / 100)


# ═══════════════════════════════════════════════════════════
# Step 3: 🔵 REFACTOR - 코드 개선
# ═══════════════════════════════════════════════════════════

# 엣지 케이스 테스트 추가 후 리팩토링
def test_trailing_stop_does_not_decrease():
    """가격 하락 시 트레일링 스탑은 유지되어야 함"""

def test_trailing_stop_trigger_detection():
    """현재가가 스탑 라인 이하로 내려오면 트리거"""
```

### 6.6 CI/CD 파이프라인 (테스트 자동화)

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run Unit Tests
        run: |
          cd backend
          pytest tests/unit -v --cov=app --cov-report=xml

      - name: Run Integration Tests
        run: |
          cd backend
          pytest tests/integration -v

      - name: Check Coverage (최소 80%)
        run: |
          cd backend
          coverage report --fail-under=80

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install & Test
        run: |
          cd frontend
          npm ci
          npm run test -- --coverage

      - name: E2E Tests (Playwright)
        run: |
          cd frontend
          npx playwright install
          npm run test:e2e
```

### 6.7 테스트 커버리지 목표

| 모듈 | 목표 | 중요도 |
|------|------|--------|
| services/risk_manager.py | 95%+ | 🔴 Critical |
| services/trading_engine.py | 90%+ | 🔴 Critical |
| services/signal_generator.py | 90%+ | 🔴 Critical |
| services/indicator.py | 95%+ | 🔴 Critical |
| services/kis_api.py | 85%+ | 🟡 High |
| ai/bnf_strategy.py | 90%+ | 🔴 Critical |
| api/*.py | 80%+ | 🟡 High |
| **전체 목표** | **85%+** | |

---

## 7. 보안 & 배포 전략

### 7.1 보안 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: 네트워크 보안                                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • HTTPS 강제 (TLS 1.3)                                │ │
│  │ • Cloudflare / AWS WAF (DDoS 방어)                    │ │
│  │ • Rate Limiting (API 호출 제한)                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 2: 인증 & 인가                                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • JWT 토큰 기반 인증 (Access + Refresh)               │ │
│  │ • 소규모 그룹용 초대 코드 방식                        │ │
│  │ • API 엔드포인트별 권한 체크                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 3: 데이터 보안                                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • 증권사 API 키: AES-256 암호화 저장                  │ │
│  │ • 비밀번호: bcrypt 해싱                               │ │
│  │ • DB 암호화 (at rest)                                 │ │
│  │ • 민감 정보 로깅 금지                                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 4: 거래 보안                                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • 일일 최대 거래 금액 제한                            │ │
│  │ • 비정상 거래 패턴 탐지 & 알림                        │ │
│  │ • 중요 설정 변경 시 2차 인증                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 환경 분리

| 환경 | API | DB | 특징 |
|------|-----|-----|------|
| Development | 모의투자 | 로컬 | 디버그 ON, Mock 데이터 |
| Staging | 모의투자 | 테스트 | 디버그 ON, 실제 시세 |
| Production | 실전투자 | 운영 | 디버그 OFF, 실제 거래 |

### 7.3 인프라 구성 (Docker)

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/kingsick
      - REDIS_URL=redis://redis:6379
      - KIS_APP_KEY=${KIS_APP_KEY}
      - KIS_APP_SECRET=${KIS_APP_SECRET}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=kingsick

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  scheduler:
    build: ./backend
    command: python -m app.scheduler.trading_loop
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/kingsick
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
      - backend

volumes:
  postgres_data:
  redis_data:
```

### 7.4 배포 옵션

| 옵션 | 설명 | 비용 |
|------|------|------|
| **Option A: VPS (추천)** | Vultr/DigitalOcean, Docker Compose 단일 서버 | 월 $20~40 |
| Option B: 클라우드 | AWS ECS / GCP Cloud Run, 자동 스케일링 | 월 $50~100+ |
| Option C: 로컬 서버 | 본인 PC 24시간, ngrok/Cloudflare Tunnel | 최소 비용 |

### 7.5 모니터링 & 알림

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  서버 모니터링                                              │
│  • Uptime Kuma (헬스체크, 다운타임 알림)                    │
│  • 자동매매 스케줄러 상태 체크                              │
│                                                             │
│  에러 트래킹                                                │
│  • Sentry (에러 수집 & 알림)                                │
│  • 주문 실패, API 오류 즉시 알림                            │
│                                                             │
│  거래 모니터링                                              │
│  • 일일 거래 요약 리포트 (텔레그램)                         │
│  • 비정상 거래 패턴 감지 시 즉시 알림                       │
│  • 손실 한도 초과 시 자동매매 일시 중지 & 알림              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.6 장애 대응

**🔴 Critical: 자동매매 중단 조건**
- 일일 손실 한도 도달 (-10% 등 사용자 설정)
- 한국투자증권 API 연결 실패 3회 연속
- 시스템 에러 발생

**🟡 Warning: 알림 발송**
- 연속 손실 발생
- API 응답 지연
- 비정상 거래 패턴 감지

**🟢 Recovery: 자동 복구**
- API 재연결 자동 시도 (exponential backoff)
- 스케줄러 자동 재시작
- DB 연결 풀 자동 복구

---

## 참고 자료

### 한국투자증권 API
- [KIS Developers 개발자센터](https://apiportal.koreainvestment.com/intro)
- [한국투자증권 GitHub 샘플코드](https://github.com/koreainvestment/open-trading-api)
- [PyKis 라이브러리](https://github.com/Soju06/python-kis)
- [WikiDocs 자동매매 튜토리얼](https://wikidocs.net/165185)

---

> 이 문서는 KingSick 프로젝트의 초기 설계안입니다.
> 개발 진행에 따라 업데이트될 수 있습니다.
