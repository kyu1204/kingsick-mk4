# AGENTS.md

Agent-focused coding guidelines for **KingSick** - AI-powered automated trading system for Korean stock market (KOSPI).

**Generated:** 2026-01-10  
**Commit:** 55050a6  
**Branch:** main

## Overview

KingSick = FastAPI backend + Next.js 14 frontend. BNF-style swing trading with KIS API integration.
Dual modes: AUTO (fully automated) / ALERT (notification + manual approval).

## Structure

```
kingsick-mk4/
├── backend/           # Python FastAPI + SQLAlchemy + uv
│   ├── app/
│   │   ├── api/       # Routers (auth, trading, watchlist) → /api/v1/*
│   │   ├── services/  # Core logic (trading_engine, kis_api, indicator)
│   │   ├── models/    # SQLAlchemy models
│   │   └── ai/        # BNF strategy (isolated from services)
│   └── tests/         # pytest (unit/integration/e2e)
├── frontend/          # Next.js 14 App Router + shadcn/ui
│   ├── app/           # Pages (dashboard, watchlist, settings)
│   ├── components/    # UI (shadcn) + domain components
│   └── lib/           # API client, auth, utils
└── docs/plans/        # Design docs + PROGRESS.md
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/` | Check `main.py` for router prefix |
| Business logic | `backend/app/services/` | Service class pattern |
| Trading strategy | `backend/app/ai/bnf_strategy.py` | Isolated from services |
| Add UI component | `frontend/components/ui/` | shadcn/ui pattern |
| Domain component | `frontend/components/{domain}/` | e.g., watchlist/, settings/ |
| API client call | `frontend/lib/api/` | Check backend first |
| Types | `frontend/types/` | Mirror backend schemas |

## Commands

### Backend (Python/uv)
```bash
cd backend
uv run pytest tests/ -v                                    # All tests
uv run pytest tests/unit/test_indicator.py -v              # Single file
uv run pytest tests/unit/test_indicator.py::TestSMA::test_sma_calculation -v  # Single test
uv run pytest tests/ -m unit -v                            # By marker
uv run pytest tests/ --cov=app --cov-report=term-missing   # Coverage
uv run ruff check app/                                     # Lint
uv run ruff check app/ --fix                               # Auto-fix
uv run ruff format app/                                    # Format
uv run mypy app/                                           # Type check
uv run uvicorn app.main:app --reload --port 8000           # Dev server
```

### Frontend (Node.js)
```bash
cd frontend
npm run test -- --run                        # All tests once
npm run test -- __tests__/lib/utils.test.ts --run  # Single file
npm run test -- --run -t "formatKRW"         # Pattern match
npm run test:coverage                        # Coverage
npm run lint                                 # ESLint
npx tsc --noEmit                             # Type check
npm run dev                                  # Dev server
```

### Docker
```bash
docker-compose up -d              # Start all
docker-compose -f docker-compose.dev.yml up -d  # Dev mode
docker-compose logs -f            # Logs
docker-compose down               # Stop
```

## Conventions

### Python (Backend)
- **Imports**: stdlib → third-party → local. Alphabetical within groups.
- **Types**: Modern syntax (`list[float]` not `List[float]`). Required on all functions.
- **Line length**: 100 chars (ruff config).
- **Docstrings**: Triple-quoted for modules, classes, public functions.
- **Errors**: Custom exception classes, never bare `except:`.

### TypeScript (Frontend)
- **Imports**: React → external libs → `@/` internal → types.
- **Path alias**: Always use `@/` for internal imports.
- **Components**: `forwardRef` for reusable, set `displayName`.
- **Styling**: Tailwind + `cn()` utility. Never inline style objects.

## Anti-Patterns (FORBIDDEN)

| Pattern | Why |
|---------|-----|
| `as any`, `@ts-ignore`, `@ts-expect-error` | Type safety violation |
| Bare `except:` in Python | Silent failures |
| Commit without tests | Untested code |
| API path guessing | Always check backend router first |
| Empty catch blocks | Silent failures |

## API Integration

All routes: `/api/v1/{router-prefix}/{endpoint}`

**Before frontend API call:**
1. Check `backend/app/api/*.py` for router prefix
2. Check `backend/app/main.py` for registration
3. Verify at `http://localhost:8000/docs`

## Testing

- **Coverage target**: 85%+ overall, 95%+ for critical modules
- **Critical modules**: risk_manager, trading_engine, signal_generator, indicator
- **Backend markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
- **Float comparisons**: Use `pytest.approx()`
- **Frontend mocks**: Check `vitest.setup.ts` before adding new mocks

## Critical Rules

1. **NEVER suppress type errors** - Fix them properly
2. **NEVER commit without tests** - Backend: `pytest`, Frontend: `vitest`
3. **ALWAYS run lint** - Backend: `ruff`, Frontend: `eslint`
4. **ALWAYS verify API paths** - Check backend router before frontend call
5. **Language**: Code/comments in English. User-facing may be Korean.
