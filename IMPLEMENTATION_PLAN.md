# Orion Implementation Plan

**Last Updated:** 2025-01-17

## Overview

Trading signals platform for identifying Option for Income (OFI) opportunities. Uses Python 3.12, Poetry, async/await throughout.

## Phase Status

| Phase | Module | Status | Notes |
|-------|--------|--------|-------|
| 1-2 | Data Layer | ✅ COMPLETE | Tested, operational |
| 3 | Technical Analysis | 🟡 PARTIAL | Files exist, need verification |
| 4 | Strategy Engine | 🟡 PARTIAL | Files exist, need verification |
| 5 | Screening Orchestration | ❌ TODO | Core + Notifications |
| 6 | CLI & Storage | ❌ TODO | CLI + Database |
| 7 | Cloud Deployment | ❌ TODO | AWS Lambda |

---

## Phase 3: Technical Analysis (VERIFICATION NEEDED)

### Status
Files exist but implementation needs verification against specs.

### Files to Verify
- `src/orion/analysis/__init__.py`
- `src/orion/analysis/indicators.py` - IndicatorCalculator class
- `src/orion/analysis/patterns.py` - PatternDetector class

### Requirements (from specs/technical-analysis.md)
1. **Indicator Calculator:**
   - SMA (20, 60 period)
   - RSI (14 period)
   - Volume Average (20 period)
   - Use pandas-ta library
   - Handle edge cases (insufficient data, empty lists)

2. **Pattern Detection:**
   - Bounce Pattern (Higher High + Higher Low)
   - Volume Confirmation (1.2x threshold)
   - Configurable lookback periods

### Tests Required
- Unit tests for each indicator calculation
- Unit tests for pattern detection
- Edge case handling

---

## Phase 4: Strategy Engine (VERIFICATION NEEDED)

### Status
Files exist but implementation needs verification against specs.

### Files to Verify
- `src/orion/strategies/__init__.py`
- `src/orion/strategies/models.py` - Strategy dataclasses
- `src/orion/strategies/parser.py` - StrategyParser class
- `src/orion/strategies/evaluator.py` - RuleEvaluator class
- `src/orion/strategies/option_analyzer.py` - OptionAnalyzer class

### Requirements (from specs/strategy-engine.md)
1. **Strategy Parser:**
   - Parse YAML files from `strategies/` directory
   - Validate all required fields
   - Handle missing/invalid fields with clear errors

2. **Rule Evaluator:**
   - Evaluate stocks against entry conditions
   - Return (matches, conditions_met, signal_strength)
   - OFI conditions: Trend, Oversold, Bounce

3. **Option Analyzer:**
   - find_atm_puts() - Find puts within 5% of current price
   - calculate_premium_yield() - Annualized yield
   - filter_by_liquidity() - Min volume 100, min OI 500
   - find_best_opportunity() - Highest yield liquid option

### Strategy File Needed
- Create `strategies/ofi.yaml` from `strategies/ofi.md`

---

## Phase 5: Screening Orchestration (TODO)

### Files to Create
- `src/orion/core/screener.py` - StockScreener class
- `src/orion/notifications/service.py` - NotificationService class
- Symbol lists in `data/` directory

### Requirements (from specs/screening-orchestration.md)
1. **Stock Screener Core:**
   - ScreeningResult model
   - screen_symbol() - Single symbol screening
   - screen_batch() - Concurrent batch screening
   - Pipeline: quote → historical → indicators → strategy → options → result
   - Max 5 concurrent with semaphore
   - Per-symbol error handling

2. **Notification Service:**
   - Email alerts for matches
   - SMTP with STARTTLS
   - HTML formatting
   - Configurable recipients

3. **Symbol List Management:**
   - File-based symbol lists
   - S&P 500 support
   - Environment variable override

---

## Phase 6: CLI and Storage (TODO)

### Files to Create
- `src/orion/cli.py` - Click CLI application
- `src/orion/storage/database.py` - Database schema
- `src/orion/storage/repository.py` - Result repository

### Requirements (from specs/cli-and-storage.md)
1. **CLI Commands:**
   - `run` - Execute screening
   - `history` - View screening history
   - `status` - Show system status

2. **Results Storage:**
   - SQLite with aiosqlite
   - screening_runs table
   - screening_results table
   - Repository interface for CRUD

3. **Configuration:**
   - ~/.orion/config.yaml
   - XDG config directory support
   - Environment variable overrides

---

## Phase 7: Cloud Deployment (TODO)

### Files to Create
- `src/orion/lambda_handler.py`
- `infrastructure/cdk_app.py`
- `deploy.sh`

### Requirements (from specs/cloud-deployment.md)
- Lambda handler with < 15 min timeout
- EventBridge scheduling
- CloudWatch monitoring
- CDK/SAM infrastructure

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

*None yet - will create after first verified working implementation*
