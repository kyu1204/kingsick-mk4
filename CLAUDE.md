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

## Phase 완료 검증 가이드라인

### 1. Task 완료 ≠ Phase 완료

**단위 테스트 통과만으로 기능 완료로 판단하지 말 것.**

각 Task는 반드시 다음을 포함해야 함:
- 서비스 로직 구현
- API 라우터 연결 (HTTP 엔드포인트 노출)
- 통합 테스트 또는 E2E 테스트
- Frontend 연동 (해당 시)

### 2. Phase 완료 전 필수 체크리스트

Phase를 완료로 선언하기 전 반드시 확인:

- [ ] 모든 서비스가 API 엔드포인트로 노출되어 있는가?
- [ ] `curl` 또는 API 클라이언트로 실제 호출이 가능한가?
- [ ] Frontend에서 Backend API 호출이 동작하는가?
- [ ] 설계 문서의 모든 요구사항이 **실제로 동작**하는가?
- [ ] E2E 시나리오 테스트를 수행했는가?
- [ ] **브라우저에서 직접 UI 테스트**를 수행했는가?

### 2-1. 브라우저 직접 테스트 (필수)

**curl/API 테스트만으로 충분하지 않음.** 실제 브라우저에서 UI가 정상 동작하는지 확인 필수.

브라우저 테스트 체크리스트:
- [ ] 페이지가 에러 없이 로드되는가?
- [ ] API 호출이 네트워크 탭에서 확인되는가?
- [ ] API 응답 데이터가 UI에 올바르게 표시되는가?
- [ ] 사용자 인터랙션(클릭, 입력 등)이 동작하는가?
- [ ] 에러 상태가 적절히 처리되는가? (로딩, 에러 메시지 등)

테스트 방법:
```bash
# 1. 서버 시작
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# 2. 브라우저에서 직접 확인 또는 Chrome MCP 도구 사용
# - mcp__claude-in-chrome__navigate
# - mcp__claude-in-chrome__computer (screenshot)
# - mcp__claude-in-chrome__read_network_requests
```

### 3. Spec Reviewer 추가 검증 항목

코드 리뷰 시 다음도 확인:

- [ ] 구현된 기능이 외부에서 접근 가능한가?
- [ ] API 엔드포인트가 올바르게 노출되어 있는가?
- [ ] 서비스 간 통합이 실제로 동작하는가?

### 4. 흔한 실수 방지

| 실수 | 올바른 접근 |
|------|------------|
| 서비스만 구현하고 API 미연결 | Task에 "API 라우터 구현" 명시적 포함 |
| 단위 테스트만 작성 | 통합/E2E 테스트도 필수 |
| "테스트 통과 = 완료" 판단 | 실제 서버 기동 후 API 호출 검증 |
| Phase 완료 후 다음 Phase 진행 | Phase 완료 체크리스트 먼저 확인 |

## 문서 기반 진행 상황 추적

### 1. 진행 상황 문서

**`docs/plans/PROGRESS.md`** - 모든 Phase/Task 진행 상황을 추적하는 마스터 문서

장비 변경 또는 세션 재시작 시 반드시 이 문서를 먼저 확인하여 현재 작업 상태를 파악.

### 2. 작업 시작 전 필수 확인

```bash
# 1. PROGRESS.md 확인
cat docs/plans/PROGRESS.md

# 2. 현재 Phase와 다음 Task 파악
# 3. Task 시작 시 상태를 "🔄 진행중"으로 업데이트
```

### 3. Task 완료 시 업데이트 필수

Task 완료 후 반드시 PROGRESS.md 업데이트:
- Task 상태: ⏳ 대기 → 🔄 진행중 → ✅ 완료
- 테스트 결과 기록 (테스트 수, 커버리지)
- Phase 검증 체크리스트 체크
- 변경 이력에 날짜와 내용 추가

### 4. 상태 코드

| 상태 | 의미 |
|------|------|
| ✅ 완료 | 구현, 테스트, 검증 모두 완료 |
| 🔄 진행중 | 현재 작업 중 |
| ⏳ 대기 | 아직 시작 안함 |
| ⚠️ 블로킹 | 다른 작업 완료 필요 |
| ❌ 취소 | 계획 변경으로 취소됨 |

### 5. 세션 재시작 시 첫 단계

1. `docs/plans/PROGRESS.md` 읽기
2. 현재 Phase 확인
3. 완료되지 않은 Task 중 다음 Task 식별
4. 해당 Task부터 작업 재개
