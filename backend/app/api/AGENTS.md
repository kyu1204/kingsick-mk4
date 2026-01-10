# API AGENTS.md

FastAPI routers. All routes under `/api/v1`.

## Structure

```
api/
├── auth.py        # /auth - Login, register, refresh, logout
├── users.py       # /users - User management
├── invitations.py # /invitations - Invite codes (admin)
├── api_keys.py    # /settings/api-key - KIS API credentials
├── watchlist.py   # /watchlist - Stock watchlist CRUD
├── stocks.py      # /stocks - Stock search
├── positions.py   # /positions - Current positions
├── trading.py     # /trading - Order execution
├── signals.py     # /signals - Trading signals
├── indicators.py  # /indicators - Technical indicators
├── telegram.py    # /telegram - Telegram bot integration
├── trades.py      # /trades - Trade history
└── schemas.py     # Shared Pydantic models
```

## Router Registration

In `main.py`:
```python
app.include_router(auth_router, prefix="/api/v1")
app.include_router(watchlist_router, prefix="/api/v1")
# ... all routers get /api/v1 prefix
```

Final path = `/api/v1` + router prefix + endpoint path.

## Authentication Pattern

```python
from app.api.auth import get_current_user, get_current_admin_user

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.get("")
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WatchlistItemResponse]:
    ...

@router.post("/admin-only")
async def admin_action(
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> dict:
    ...
```

## Schema Location

- **Shared schemas**: `api/schemas.py` (IndicatorRequest, SignalResponse, etc.)
- **Endpoint-specific**: Defined in router file (RegisterRequest, LoginRequest, etc.)

## Error Handling

```python
from app.services.watchlist import WatchlistError

@router.post("")
async def add_item(...):
    try:
        return await service.add_item(user_id, data)
    except WatchlistError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
```

## Response Pattern

```python
class WatchlistItemResponse(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    
    class Config:
        from_attributes = True  # Enable ORM mode
```

## Swagger

Dev only: `http://localhost:8000/docs`
Check actual paths and schemas before frontend integration.
