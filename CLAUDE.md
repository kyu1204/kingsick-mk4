# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KingSick is an AI-powered automated trading system for Korean stock market (KOSPI) using BNF-style swing trading strategies. It integrates with Korea Investment & Securities API for real-time market data and order execution.

**Key Features:**
- Dual trading modes: AUTO (fully automated) and ALERT (notification with manual approval)
- AI signal generation based on technical indicators (RSI, MA, MACD, Bollinger Bands)
- Risk management with stop-loss, take-profit, and trailing stop
- Real-time notifications via Telegram/Slack

## Tech Stack

**Frontend:** Next.js 14 + TypeScript + TailwindCSS + shadcn/ui + Lightweight Charts
**Backend:** Python FastAPI + SQLAlchemy + APScheduler
**Database:** PostgreSQL (main) + Redis (cache) + TimescaleDB (time-series)
**External APIs:** Korea Investment & Securities REST API (PyKis), Telegram Bot, Slack Webhook

## Project Structure

```
kingsick/
├── frontend/           # Next.js app
│   ├── app/           # App router pages (dashboard, watchlist, settings, analysis)
│   ├── components/    # UI components (charts, trading, layout)
│   └── lib/           # API client, WebSocket client
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI routers (auth, trading, watchlist, positions)
│   │   ├── models/    # SQLAlchemy models (user, trade, position, settings)
│   │   ├── services/  # Business logic (kis_api, trading_engine, signal_generator, risk_manager)
│   │   ├── ai/        # ML models (bnf_strategy, pattern_detector)
│   │   └── scheduler/ # APScheduler trading loop
│   └── tests/         # pytest tests (unit, integration, e2e)
└── docs/plans/        # Design documents
```

## Development Commands

### Backend (Python with uv)
```bash
cd backend

# Install dependencies (uv - fast Python package manager)
uv sync --all-extras          # Install all dependencies including dev
uv sync                       # Install production dependencies only

# Run server
uv run uvicorn app.main:app --reload --port 8000

# Run tests
uv run pytest tests/unit -v                    # Run unit tests
uv run pytest tests/integration -v             # Run integration tests
uv run pytest tests/e2e -v                     # Run e2e tests
uv run pytest tests/unit/test_indicator.py -v  # Run single test file
uv run pytest tests/ --cov=app --cov-report=html  # With coverage report

# Linting & Formatting (ruff - fast Python linter)
uv run ruff check .           # Check for linting errors
uv run ruff check . --fix     # Auto-fix linting errors
uv run ruff format .          # Format code

# Type checking
uv run mypy app/              # Run type checker
```

### Frontend (Node.js)
```bash
cd frontend
npm install                    # Install dependencies

# Run dev server
npm run dev                    # Start development server (port 3000)
npm run build                  # Production build
npm run start                  # Start production server

# Run tests (Vitest)
npm run test                   # Run tests in watch mode
npm run test:coverage          # Run tests with coverage report
npm run test:ui                # Run tests with UI

# Linting & Type checking
npm run lint                   # Run ESLint
npx tsc --noEmit               # Type check without emitting

# E2E tests (Playwright - to be configured)
npx playwright install
npm run test:e2e
```

### Docker
```bash
docker-compose up -d          # Start all services
docker-compose logs -f        # View logs
docker-compose down           # Stop services
```

## Architecture Notes

### Trading Engine Flow
1. Scheduler runs every minute via APScheduler
2. Fetches market data from KIS API for watchlist + positions
3. Calculates technical indicators (MA, RSI, MACD, Bollinger)
4. AI model generates BUY/SELL/HOLD signals with confidence score
5. Risk manager validates against stop-loss/take-profit/limits
6. AUTO mode: executes order directly | ALERT mode: sends notification for approval

### BNF Strategy Rules
- BUY: RSI < 30 + volume spike + below lower Bollinger band
- SELL: RSI > 70 + volume decrease + above upper Bollinger band
- Golden/Death cross confirmation via 5/20 MA

### Security Considerations
- KIS API credentials stored AES-256 encrypted
- JWT authentication with refresh tokens
- All trading-critical settings require re-authentication
- Daily loss limits with automatic trading halt

## Testing Strategy

Target coverage: 85%+ overall, 95%+ for critical modules (risk_manager, trading_engine, signal_generator, indicator)

Testing pyramid: 60% unit / 30% integration / 10% E2E

Critical test cases focus on:
- Technical indicator calculations
- Signal generation accuracy
- Risk management triggers (stop-loss, take-profit, trailing stop)
- Order execution flow
- API error handling

## 필수 검증 규칙 (MANDATORY - 반드시 준수)

### 코드 변경 후 자동 실행 (트리거 규칙)

**Backend 코드 변경 시 (app/ 디렉토리):**
```bash
cd backend && uv run pytest tests/ -v --tb=short
cd backend && uv run ruff check app/
```

**Frontend 코드 변경 시 (frontend/ 디렉토리):**
```bash
cd frontend && npm run test -- --run
cd frontend && npm run lint
```

⚠️ **위 명령어는 코드 변경 후 사용자 요청 없이도 자동으로 실행해야 함**

### Task/Phase 완료 조건 (필수 체크리스트)

Task를 "완료"로 표시하기 전 **모든 항목이 충족**되어야 함:

```
[ ] Backend 테스트 통과: uv run pytest tests/ -v
[ ] Frontend 테스트 통과: npm run test -- --run
[ ] Backend lint 통과: uv run ruff check app/
[ ] Frontend lint 통과: npm run lint
[ ] 브라우저 E2E 테스트 수행 (해당 기능)
[ ] PROGRESS.md 업데이트
```

### 금지 사항

❌ 테스트 실행 없이 Task 완료 표시
❌ lint 에러 무시하고 커밋
❌ "나중에 테스트" 약속하고 넘어가기
❌ 사용자가 요청하지 않았다는 이유로 테스트 건너뛰기

### 예외 상황

다음 경우에만 테스트 생략 가능 (반드시 사용자에게 알림):
- 문서만 수정한 경우 (*.md 파일)
- 설정 파일만 수정한 경우 (환경변수 등)
- 사용자가 명시적으로 테스트 생략 요청한 경우

## Environment Variables

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
KIS_APP_KEY=
KIS_APP_SECRET=
JWT_SECRET=
ENCRYPTION_KEY=
TELEGRAM_BOT_TOKEN=
SLACK_WEBHOOK_URL=
```

## Language

All code comments, variable names, and technical documentation should be in English. User-facing content and design documents may be in Korean.

## 프론트엔드-백엔드 연동 규칙

### API 연동 전 필수 확인 (MANDATORY)

프론트엔드에서 API 호출 코드 작성 전 **반드시** 다음을 확인:

1. **백엔드 라우터 코드 직접 확인**
   - `backend/app/api/*.py` 파일에서 실제 `prefix` 확인
   - `backend/app/main.py`에서 라우터 등록 prefix 확인
   - 최종 경로 = main.py prefix + router prefix + endpoint path

2. **Swagger 문서 참조**
   - 백엔드 실행 후 `http://localhost:8000/docs` 에서 실제 API 스펙 확인
   - Request/Response 스키마 확인

### 연동 작업 체크리스트

```
[ ] 백엔드 라우터 파일에서 prefix 확인
[ ] main.py에서 라우터 등록 경로 확인
[ ] Swagger UI에서 실제 경로 검증
[ ] 프론트엔드 API 클라이언트 코드 작성
[ ] 실제 API 호출 테스트 (브라우저 Network 탭)
```

### 경로 불일치 방지

**잘못된 예시 (추측 기반):**
```typescript
// 설계 문서만 보고 추측으로 작성 - 금지
await apiClient.get('/api/v1/settings/api-key');
```

**올바른 예시 (코드 확인 후):**
```typescript
// backend/app/api/api_keys.py의 prefix="/settings/api-key" 확인
// backend/app/main.py의 prefix="/api/v1" 확인
// 최종: /api/v1 + /settings/api-key = /api/v1/settings/api-key
await apiClient.get('/api/v1/settings/api-key');
```

## 작업 프로세스 (Skills 참조)

### Phase/Task 완료 시
**`/phase-completion` skill 반드시 invoke** - 브라우저 E2E 테스트 포함 전체 검증

### 세션 시작/재개 시
**`/progress-tracking` skill invoke** - PROGRESS.md 기반 현재 상태 파악

### 진행 상황 문서
**`docs/plans/PROGRESS.md`** - 모든 Phase/Task 상태 추적의 Single Source of Truth
