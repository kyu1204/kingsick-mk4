# Suggested Commands

## Backend (Python FastAPI)
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit -v --cov=app

# Run integration tests
pytest tests/integration -v

# Run single test file
pytest tests/unit/test_indicator.py -v

# Run single test function
pytest tests/unit/test_indicator.py::test_rsi_oversold_detection -v

# Coverage report
pytest tests/ --cov=app --cov-report=html
```

## Frontend (Next.js)
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm run test
npm run test -- --coverage

# Run single test
npm run test -- -t "test name"

# E2E tests (Playwright)
npx playwright install
npm run test:e2e
```

## Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

## Database
```bash
# PostgreSQL shell (via Docker)
docker-compose exec db psql -U user -d kingsick

# Redis CLI
docker-compose exec redis redis-cli
```

## System Commands (Darwin/macOS)
- `ls -la` - List files with details
- `find . -name "*.py"` - Find Python files
- `grep -r "pattern" --include="*.py"` - Search in Python files
- `pbcopy` / `pbpaste` - Clipboard operations
