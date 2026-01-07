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

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/unit -v --cov=app
pytest tests/integration -v
pytest tests/e2e -v

# Run single test file
pytest tests/unit/test_indicator.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
```

### Frontend (Node.js)
```bash
cd frontend
npm install

# Run dev server
npm run dev

# Run tests
npm run test
npm run test -- --coverage

# E2E tests
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
