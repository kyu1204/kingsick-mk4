# KingSick Backend

AI-powered automated trading system for Korean stock market (KOSPI).

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run development server
uv run uvicorn app.main:app --reload --port 8000

# Run tests
uv run pytest tests/unit -v
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
