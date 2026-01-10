# Tests AGENTS.md

pytest-based testing with async support.

## Structure

```
tests/
├── unit/           # Pure logic tests (no DB, no network)
│   ├── test_indicator.py
│   ├── test_bnf_strategy.py
│   ├── test_risk_manager.py
│   └── ...
├── integration/    # API + DB tests
│   ├── test_api_auth.py
│   ├── test_api_watchlist.py
│   └── ...
├── e2e/            # Full system tests (WIP)
└── conftest.py     # Shared fixtures
```

## Commands

```bash
# All tests
uv run pytest tests/ -v

# By marker
uv run pytest tests/ -m unit -v
uv run pytest tests/ -m integration -v

# Single file
uv run pytest tests/unit/test_indicator.py -v

# Single test
uv run pytest tests/unit/test_indicator.py::TestSMA::test_sma_calculation -v

# Coverage
uv run pytest tests/ --cov=app --cov-report=term-missing
```

## Fixtures (conftest.py)

```python
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

@pytest.fixture
def test_settings() -> dict[str, Any]:
    """Test environment settings."""
    ...
```

## Test Environment

Set automatically in `conftest.py`:
- `ENVIRONMENT=test`
- `DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/kingsick_test`
- `JWT_SECRET=test-secret-key-for-testing-only`

## Patterns

### Unit Test
```python
class TestSMA:
    """Tests for Simple Moving Average."""

    def test_sma_calculation(self):
        calc = IndicatorCalculator()
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calc.calculate_sma(prices, period=3)
        assert result[2] == pytest.approx(20.0)
```

### Integration Test
```python
@pytest.mark.integration
async def test_login_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Coverage Targets

| Module | Target |
|--------|--------|
| Overall | 85%+ |
| risk_manager | 95%+ |
| trading_engine | 95%+ |
| signal_generator | 95%+ |
| indicator | 95%+ |

## Anti-Patterns

- Never skip tests without explicit marker
- Never use `pytest.approx()` for exact matches
- Never hardcode test data that should come from fixtures
