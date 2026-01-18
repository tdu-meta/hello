## Build & Run

Succinct rules for how to BUILD the project:

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest tests/unit

# Run integration tests (requires ALPHA_VANTAGE_API_KEY)
poetry run pytest tests/integration

# Run with coverage
poetry run pytest --cov=src/orion --cov-report=html

# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff check src/ tests/

# Type check
poetry run mypy src/
```

## Validation

Run these after implementing to get immediate feedback:

- Tests: `poetry run pytest` (all tests), `poetry run pytest tests/unit` (unit only)
- Typecheck: `poetry run mypy src/`
- Lint: `poetry run ruff check src/ tests/`

## Project Structure

```
src/orion/
├── data/           # Data layer (COMPLETE - Phase 1-2)
│   ├── models.py           # Quote, OptionChain, OHLCV, TechnicalIndicators, etc.
│   ├── provider.py         # DataProvider abstract interface
│   ├── cache.py            # CacheManager with TTL
│   └── providers/
│       ├── yahoo_finance.py     # Quotes, options, historical data
│       └── alpha_vantage.py     # Company fundamentals, quotes
├── analysis/       # Technical analysis (TODO - Phase 3)
├── strategies/     # Strategy engine (TODO - Phase 4)
├── core/          # Screening orchestration (TODO - Phase 5)
├── notifications/ # Alert service (TODO - Phase 5)
├── storage/       # Database layer (TODO - Phase 6)
└── cli.py         # Command-line interface (TODO - Phase 6)
```

## Code Conventions

- Python 3.12 only
- Use `async/await` for all I/O operations
- Type hints required on all public functions
- Use `Decimal` from `decimal` module for financial calculations
- Use dataclasses for data models
- Use structlog for structured logging (JSON format)

## Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
# ALPHA_VANTAGE_API_KEY=your_key_here
```

## Known Working Commands

```bash
# Demo the data layer
poetry run python examples/alpha_vantage_demo.py

# Run specific test file
poetry run pytest tests/unit/test_data_models.py -v
```
