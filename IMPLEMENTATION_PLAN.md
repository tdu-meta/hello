# Orion Implementation Plan

**Last Updated:** 2025-01-17

## Overview

Trading signals platform for identifying Option for Income (OFI) opportunities. Uses Python 3.12, Poetry, async/await throughout.

## Phase Status

| Phase | Module | Status | Notes |
|-------|--------|--------|-------|
| 1-2 | Data Layer | ✅ COMPLETE | Tested, operational |
| 3 | Technical Analysis | ✅ COMPLETE | All indicators and patterns implemented |
| 4 | Strategy Engine | ✅ COMPLETE | Parser, evaluator, option analyzer working |
| 5 | Screening Orchestration | ✅ COMPLETE | Core screener + notifications |
| 6 | CLI & Storage | ✅ COMPLETE | CLI + SQLite with aiosqlite |
| 7 | Cloud Deployment | ✅ COMPLETE | AWS Lambda + CDK infrastructure |

---

## Phase 3: Technical Analysis (COMPLETE)

### Summary
All technical analysis functionality has been implemented and tested.

### Files
- `src/orion/analysis/__init__.py`
- `src/orion/analysis/indicators.py` - IndicatorCalculator class
- `src/orion/analysis/patterns.py` - PatternDetector class

### Implemented Features
1. **Indicator Calculator:**
   - SMA (20, 60 period) ✅
   - RSI (14 period) ✅
   - Volume Average (20 period) ✅
   - Uses pandas-ta library ✅
   - Handles edge cases (insufficient data, empty lists) ✅

2. **Pattern Detection:**
   - Bounce Pattern (Higher High + Higher Low) ✅
   - Volume Confirmation (1.2x threshold) ✅
   - Configurable lookback periods ✅

### Tests
- All 33 tests passing for indicators and patterns

---

## Phase 4: Strategy Engine (COMPLETE)

### Summary
All strategy engine components have been implemented and tested.

### Files
- `src/orion/strategies/__init__.py`
- `src/orion/strategies/models.py` - Strategy dataclasses
- `src/orion/strategies/parser.py` - StrategyParser class
- `src/orion/strategies/evaluator.py` - RuleEvaluator class
- `src/orion/strategies/option_analyzer.py` - OptionAnalyzer class
- `strategies/ofi.yaml` - OFI strategy configuration

### Implemented Features
1. **Strategy Parser:**
   - Parse YAML files from `strategies/` directory ✅
   - Validate all required fields ✅
   - Handle missing/invalid fields with clear errors ✅

2. **Rule Evaluator:**
   - Evaluate stocks against entry conditions ✅
   - Return (matches, conditions_met, signal_strength) ✅
   - OFI conditions: Trend, Oversold, Bounce ✅

3. **Option Analyzer:**
   - find_atm_puts() - Find puts within 5% of current price ✅
   - calculate_premium_yield() - Annualized yield ✅
   - filter_by_liquidity() - Min volume 100, min OI 500 ✅
   - find_best_opportunity() - Highest yield liquid option ✅

### Tests
- All 38 tests passing for strategy engine

---

## Phase 5: Screening Orchestration (COMPLETE)

### Summary
Phase 5 has been successfully implemented with all required components passing tests. The screening orchestration system provides a robust pipeline for identifying OFI opportunities through concurrent screening, comprehensive error handling, and configurable notifications.

### Files Created
- `src/orion/core/screener.py` - StockScreener class with concurrent screening
- `src/orion/notifications/service.py` - NotificationService for email alerts
- `src/orion/notifications/models.py` - NotificationConfig dataclass
- `tests/unit/test_core_screener.py` - Tests for StockScreener
- `tests/unit/test_notifications.py` - Tests for NotificationService

### Key Features Implemented
1. **Stock Screener Core:**
   - ScreeningResult model for structured output ✅
   - screen_symbol() for single symbol analysis ✅
   - screen_batch() with concurrent processing using asyncio ✅
   - Complete pipeline: quote → historical → indicators → strategy → options → result ✅
   - Maximum 5 concurrent requests with semaphore for rate limiting ✅
   - Per-symbol error handling to ensure one failure doesn't stop the batch ✅
   - ScreeningStats for batch operation statistics ✅

2. **Notification Service:**
   - Email alerts for trading opportunities ✅
   - SMTP configuration with STARTTLS support ✅
   - HTML-formatted emails with comprehensive details ✅
   - Configurable recipients via environment variables ✅
   - Graceful handling of email service failures ✅
   - Batch alert support for multiple matches ✅

3. **Symbol List Management:**
   - Screen multiple symbols concurrently ✅
   - Filter and return matches only ✅
   - Statistics tracking (success rate, duration) ✅

### Tests
- All 27 tests passing for screener and notifications
- Total: 175 unit tests passing

---



## Phase 6: CLI and Storage (COMPLETE)

### Summary
Phase 6 has been successfully implemented with all required components passing tests. The CLI provides commands for running screenings, viewing history, and checking system status. The storage layer provides SQLite persistence with async/await support.

### Files Created
- `src/orion/cli.py` - Click CLI application with run/history/status commands
- `src/orion/storage/__init__.py` - Storage module exports
- `src/orion/storage/database.py` - Database class with schema management
- `src/orion/storage/repository.py` - ResultRepository for CRUD operations
- `tests/unit/test_storage.py` - Tests for storage module (18 tests)

### Key Features Implemented
1. **CLI Commands:**
   - `run` - Execute screening with --strategy, --symbols, --notify, --dry-run options ✅
   - `history` - View screening history with --symbol, --days, --matches-only filters ✅
   - `status` - Show system status including last run, statistics, config ✅

2. **Database Schema:**
   - screening_runs table (id, timestamp, strategy_name, symbols_count, matches_count, duration_seconds) ✅
   - screening_results table (id, run_id, symbol, timestamp, matches, signal_strength, conditions_met/missed, quote/indicators/option JSON) ✅
   - Indexes on run_id, symbol, timestamp, matches for efficient queries ✅
   - Foreign key with CASCADE delete for referential integrity ✅

3. **Repository Interface:**
   - save_run() - Save screening run metadata ✅
   - save_result() - Save individual screening result ✅
   - save_results() - Save multiple results ✅
   - get_results_by_symbol() - Query history by symbol ✅
   - get_recent_matches() - Get recent matching results ✅
   - get_statistics() - Aggregate statistics ✅
   - get_recent_runs() - Recent screening runs ✅

4. **Configuration:**
   - XDG config directory support (~/.config/orion/) ✅
   - Database stored at ~/.config/orion/data/screenings.db ✅
   - Default strategy path resolution ✅
   - NotificationConfig from environment variables ✅

### Dependencies Added
- aiosqlite ^0.19 - Async SQLite operations
- pyxdg ^0.27 - XDG directory support

### Tests
- All 18 tests passing for storage module
- Total: 193 unit tests passing (175 + 18 new)

---

## Phase 7: Cloud Deployment (COMPLETE)

### Summary
Phase 7 has been successfully implemented with all required components passing tests. The cloud deployment enables automated stock screening via AWS Lambda with EventBridge scheduling and CloudWatch monitoring.

### Files Created
- `src/orion/lambda_handler.py` - Lambda entry point with event parsing and screening orchestration
- `infrastructure/cdk_app.py` - CDK application for stack deployment
- `infrastructure/lib/orion_stack.py` - CDK stack with Lambda, EventBridge, CloudWatch resources
- `infrastructure/cdk.json` - CDK configuration
- `deploy.sh` - Deployment script with prerequisite checks
- `tests/unit/test_lambda_handler.py` - Tests for Lambda handler (18 tests)

### Key Features Implemented
1. **Lambda Handler:**
   - `handler(event, context)` - Lambda entry point ✅
   - Event schema parsing (strategy, symbols, notify, dry_run) ✅
   - Strategy file resolution (supports Lambda /opt and local paths) ✅
   - Config loading from environment variables ✅
   - Async screening execution with timeout handling ✅
   - JSON-serializable response format ✅
   - Structured CloudWatch logging ✅
   - Local testing support via `python -m orion.lambda_handler` ✅

2. **Infrastructure as Code (CDK):**
   - Lambda function with Python 3.12 runtime ✅
   - Lambda timeout: 15 minutes (maximum) ✅
   - Lambda memory: 1024 MB (configurable) ✅
   - CloudWatch Log Group with 1-week retention ✅
   - EventBridge rule for scheduled execution ✅
   - IAM role with minimal permissions (CloudWatch Logs only) ✅
   - CloudWatch Alarms (error rate, duration) ✅
   - Environment variable configuration ✅

3. **Deployment Script:**
   - Prerequisite checks (Python, Node.js, CDK, Docker) ✅
   - AWS credential validation ✅
   - CDK bootstrap if needed ✅
   - Environment variable passthrough for secrets ✅
   - Support for custom AWS profiles and regions ✅
   - Deployment output with Lambda invoke and log viewing commands ✅

4. **Environment Configuration:**
   - `DATA_PROVIDER__provider` - yahoo_finance or alpha_vantage ✅
   - `DATA_PROVIDER__api_key` - Alpha Vantage API key ✅
   - `NOTIFICATIONS__*` - SMTP configuration for alerts ✅
   - `DEFAULT_SYMBOLS` - Symbols for scheduled runs ✅
   - `SCHEDULE_EXPRESSION` - EventBridge cron/rate expression ✅
   - `SCHEDULE_ENABLED` - Enable/disable scheduling ✅

### Dependencies Added
- aws-cdk-lib ^2.100 - AWS CDK library
- constructs ^10.3 - CDK constructs base

### Tests
- All 18 tests passing for Lambda handler
- Total: 211 unit tests passing (193 + 18 new)

### Deployment Instructions
```bash
# Set environment variables
export ALPHA_VANTAGE_API_KEY="your_key"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="user"
export SMTP_PASSWORD="password"
export NOTIFICATION_FROM="alerts@example.com"
export NOTIFICATION_TO='["recipient@example.com"]'

# Deploy to AWS
./deploy.sh

# Or with custom options
./deploy.sh --profile prod --region us-west-2 --schedule "rate(4 hours)"
```

### Manual Lambda Invocation
```bash
aws lambda invoke \
  --function-name orion-screening \
  --payload '{"strategy":"ofi","symbols":["AAPL"],"notify":false}' \
  response.json
```

### View CloudWatch Logs
```bash
aws logs tail /aws/lambda/orion-screening --follow
```

---

## Commands Reference

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest          # All tests
poetry run pytest tests/unit    # Unit only
poetry run pytest tests/integration  # Integration only (requires ALPHA_VANTAGE_API_KEY)

# Type check
poetry run mypy src/

# Lint
poetry run ruff check src/ tests/

# Format
poetry run black src/ tests/

# Run with coverage
poetry run pytest --cov=src/orion --cov-report=html
```

---

## Issues Found

### Resolved
*None yet*

### Open
*None yet*

---

## Git Tags

- `v0.0.1` - All 7 phases complete, 211 tests passing
