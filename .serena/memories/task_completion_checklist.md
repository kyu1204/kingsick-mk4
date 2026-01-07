# Task Completion Checklist

When completing a task, ensure the following steps are done:

## Before Committing

### Backend (Python)
1. Run linting: `cd backend && ruff check .` or `flake8`
2. Run formatting: `black .` and `isort .`
3. Run type checking: `mypy app/`
4. Run tests: `pytest tests/ -v`
5. Check coverage meets target (85%+ overall, 95%+ for critical modules)

### Frontend (TypeScript)
1. Run linting: `cd frontend && npm run lint`
2. Run formatting: `npm run format` (if configured)
3. Run type checking: `npm run type-check` or `tsc --noEmit`
4. Run tests: `npm run test`

## Critical Modules (Require 95%+ Coverage)
- `services/risk_manager.py` - Risk management logic
- `services/trading_engine.py` - Trading execution
- `services/signal_generator.py` - AI signal generation
- `services/indicator.py` - Technical indicator calculations
- `ai/bnf_strategy.py` - BNF strategy rules

## Security Checks
- No hardcoded credentials or API keys
- Sensitive data properly encrypted (AES-256 for KIS credentials)
- Input validation on all API endpoints
- No sensitive data in logs

## Trading-Specific Checks
- Risk limits properly enforced (stop-loss, max investment)
- Order validation before execution
- Error handling for API failures
- Proper rollback mechanisms
