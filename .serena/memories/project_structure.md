# Project Structure

## Directory Layout (Planned)
```
kingsick/
├── frontend/                     # Next.js 14 frontend
│   ├── app/                      # App router
│   │   ├── (auth)/              # Auth pages (login, register)
│   │   ├── dashboard/           # Main dashboard, positions, trades
│   │   ├── watchlist/           # Stock watchlist management
│   │   ├── analysis/            # AI analysis (Phase 4)
│   │   ├── backtest/            # Backtesting (Phase 4)
│   │   └── settings/            # User settings
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── charts/              # Trading charts (Lightweight Charts)
│   │   ├── trading/             # Trading-specific components
│   │   └── layout/              # Layout components
│   └── lib/
│       ├── api.ts               # API client
│       └── websocket.ts         # WebSocket client
│
├── backend/                      # Python FastAPI
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Database connection
│   │   ├── api/                 # API routers
│   │   ├── models/              # SQLAlchemy models
│   │   ├── services/            # Business logic
│   │   │   ├── kis_api.py       # Korea Investment API
│   │   │   ├── trading_engine.py
│   │   │   ├── signal_generator.py
│   │   │   ├── risk_manager.py
│   │   │   ├── indicator.py     # Technical indicators
│   │   │   └── alert.py         # Telegram/Slack notifications
│   │   ├── ai/                  # ML models
│   │   │   ├── bnf_strategy.py
│   │   │   └── pattern_detector.py
│   │   └── scheduler/           # APScheduler
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── docs/plans/                   # Design documents
├── docker-compose.yml
└── CLAUDE.md
```

## Key Architecture Components

### Trading Engine Flow
Scheduler (1min) → Market Data → Indicators → AI Signal → Risk Check → Order Execution

### Database Schema (PostgreSQL)
- `users` - User accounts and KIS API credentials (encrypted)
- `watchlist` - Watched stocks per user
- `trading_settings` - Mode, stop-loss, take-profit settings
- `trades` - Trade history with AI reasoning
- `positions` - Current holdings
- `alert_settings` - Telegram/Slack configuration
