# Code Style and Conventions

## General
- Code comments, variable names, and technical documentation: **English**
- User-facing content and design documents: **Korean** allowed

## Python (Backend)
- Follow PEP 8 style guide
- Use type hints for all function signatures
- Use Pydantic models for API request/response validation
- Use async/await for I/O operations
- Docstrings: Google style format
- Import order: stdlib → third-party → local (use isort)
- Max line length: 88 (Black formatter)

### Naming Conventions
- Classes: `PascalCase` (e.g., `TradingEngine`, `RiskManager`)
- Functions/methods: `snake_case` (e.g., `calculate_rsi`, `place_order`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_INVESTMENT`, `DEFAULT_STOP_LOSS`)
- Private methods: `_leading_underscore`

### Project Patterns
- Services layer for business logic (`services/`)
- Models for database entities (`models/`)
- API routers separate from business logic (`api/`)
- AI/ML models isolated in `ai/` directory

## TypeScript (Frontend)
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use shadcn/ui component library
- TailwindCSS for styling (no inline styles)
- File naming: `kebab-case.tsx` for components

### Naming Conventions
- Components: `PascalCase` (e.g., `DashboardCard`, `TradeList`)
- Hooks: `useCamelCase` (e.g., `useWebSocket`, `useTrades`)
- Utilities: `camelCase`

## Testing
- Test file naming: `test_*.py` (Python), `*.test.tsx` (TypeScript)
- Use descriptive test names that explain the behavior
- Follow AAA pattern: Arrange, Act, Assert
- Mock external APIs (KIS API, Telegram, etc.)
