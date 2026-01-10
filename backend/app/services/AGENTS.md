# Services AGENTS.md

Core business logic layer. All services follow consistent patterns.

## Structure

```
services/
├── trading_engine.py   # 807 lines - Core trading loop (largest file)
├── kis_api.py          # 562 lines - KIS API client
├── indicator.py        # 471 lines - Technical indicators
├── telegram_service.py # 356 lines - Telegram notifications
├── watchlist.py        # 354 lines - Watchlist management
├── auth.py             # 342 lines - JWT, user management
├── risk_manager.py     # 301 lines - Stop-loss, take-profit
├── signal_generator.py # Signal generation from indicators
└── encryption.py       # AES-256 for API keys
```

## Service Class Pattern

```python
class WatchlistService:
    """Service for watchlist CRUD operations."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def get_items(self, user_id: str) -> list[WatchlistItem]:
        """Get all watchlist items for user."""
        ...
    
    async def add_item(self, user_id: str, data: WatchlistItemCreate) -> WatchlistItem:
        """Add item to watchlist."""
        ...
```

## Error Pattern

Each service defines its own exceptions:

```python
# In service file
class WatchlistError(Exception):
    """Base exception for watchlist operations."""
    pass

class WatchlistItemNotFoundError(WatchlistError):
    """Item not found."""
    pass
```

## Key Modules

### trading_engine.py (CRITICAL - 95% coverage required)
- `TradingEngine` class orchestrates all trading
- `run_trading_loop()`: Main scheduler entry
- `approve_alert()`, `reject_alert()`: Manual approval flow
- Uses `KISApiClient`, `IndicatorCalculator`, `RiskManager`

### indicator.py (CRITICAL - 95% coverage required)
- `IndicatorCalculator` class
- Methods: `calculate_sma`, `calculate_ema`, `calculate_rsi`, `calculate_macd`, `calculate_bollinger_bands`
- BNF helpers: `is_oversold`, `is_overbought`, `detect_golden_cross`, `detect_death_cross`

### risk_manager.py (CRITICAL - 95% coverage required)
- Stop-loss, take-profit, trailing stop calculations
- Position sizing based on risk tolerance
- Daily loss limit enforcement

## Async Pattern

All external I/O uses async:

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers)
```

## Testing

Tests mirror this structure in `tests/unit/`:
- `test_trading_engine.py`
- `test_indicator.py`
- `test_risk_manager.py`
- etc.

Use `pytest.approx()` for float comparisons in indicator tests.
