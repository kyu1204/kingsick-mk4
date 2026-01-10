# Backend AGENTS.md

Python FastAPI backend with SQLAlchemy + APScheduler. Uses `uv` for package management.

## Structure

```
backend/
├── app/
│   ├── api/           # FastAPI routers → See api/AGENTS.md
│   ├── services/      # Business logic → See services/AGENTS.md
│   ├── models/        # SQLAlchemy models (user, watchlist, telegram_link)
│   ├── ai/            # Trading strategy (bnf_strategy.py)
│   ├── scheduler/     # APScheduler trading loop
│   ├── config.py      # Pydantic BaseSettings
│   └── database.py    # AsyncSession setup
├── tests/             # See tests/AGENTS.md
├── alembic/           # DB migrations
└── pyproject.toml     # Dependencies + tool configs
```

## Commands

```bash
# Dev
uv run uvicorn app.main:app --reload --port 8000

# Test
uv run pytest tests/ -v
uv run pytest tests/unit/test_indicator.py::TestSMA::test_sma_calculation -v

# Lint & Format
uv run ruff check app/
uv run ruff check app/ --fix
uv run ruff format app/
uv run mypy app/
```

## Conventions

### Import Order
```python
# stdlib
import math
from collections.abc import AsyncGenerator
from typing import Annotated

# third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# local
from app.config import get_settings
from app.services.auth import authenticate_user
```

### Type Hints
- Required on ALL functions
- Modern syntax: `list[float]`, `dict[str, Any]`, `User | None`
- Use `Annotated` for FastAPI dependencies

### Error Handling
```python
# Define custom exceptions in services
class AuthenticationError(Exception):
    pass

# Catch in API layer, convert to HTTPException
try:
    user = await authenticate_user(db, email, password)
except AuthenticationError as e:
    raise HTTPException(status_code=401, detail=str(e)) from e
```

### Docstrings
```python
def calculate_rsi(self, prices: list[float], period: int = 14) -> list[float]:
    """Calculate Relative Strength Index.

    Args:
        prices: List of price values
        period: RSI period (default: 14)

    Returns:
        List of RSI values (NaN for indices before enough data)
    """
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `services/trading_engine.py` | Core trading loop, AUTO/ALERT modes | 807 |
| `services/kis_api.py` | KIS API client | 562 |
| `services/indicator.py` | Technical indicators (SMA, RSI, MACD, Bollinger) | 471 |
| `api/schemas.py` | Pydantic models (centralized) | 382 |

## Config

From `pyproject.toml`:
- **Python**: 3.11+
- **Line length**: 100 (ruff)
- **Ruff rules**: E, F, I, N, W, UP
- **MyPy**: strict mode, ignore_missing_imports

## Anti-Patterns

- Never use bare `except:`
- Never suppress types with `# type: ignore`
- Never hardcode secrets (use config.py)
- Never commit without running `pytest` and `ruff`
