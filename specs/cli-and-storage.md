# CLI and Storage Module

## Overview
Provide command-line interface for running screenings and persist results to database for historical analysis.

## Topics

### 1. CLI Interface
Command-line tool for running screenings and querying results.

**Commands:**

`run` - Execute screening
- `--strategy` - Strategy file path (required)
- `--symbols` - Comma-separated symbols (optional, uses default list)
- `--notify/--no-notify` - Send notifications (default: false)
- `--dry-run` - Show matches without saving/notifying

`history` - View screening history
- `--symbol` - Filter by symbol
- `--days` - Days to look back (default: 30)
- `--count` - Max results to show

`status` - Show system status
- Last screening run time
- Recent matches
- Cache statistics

**Requirements:**
- Use Click framework
- Async command execution
- Progress bars for batch screening
- Colored terminal output

### 2. Results Storage
Persist screening results to database for analysis.

**Database Schema:**

screening_runs table:
- id (PK)
- timestamp
- strategy_name
- symbols_count
- matches_count
- duration_seconds

screening_results table:
- id (PK)
- run_id (FK)
- symbol
- timestamp
- matches (boolean)
- signal_strength
- conditions_met (JSON)
- quote_data (JSON)
- indicators_data (JSON)
- option_recommendation (JSON)

**Repository Interface:**
- `save_run(run)` - Save screening run metadata
- `save_result(result, run_id)` - Save individual result
- `get_results_by_symbol(symbol, days)` - Query history
- `get_recent_matches(days, limit)` - Get recent matches
- `get_statistics()` - Aggregate stats

**Requirements:**
- SQLite for local storage
- Async database operations (aiosqlite)
- Auto-schema creation on first run
- Query methods for common use cases

### 3. Configuration
CLI-specific configuration management.

**Config File: `~/.orion/config.yaml`**
- Default strategy path
- Default symbol list
- Notification preferences
- Database path
- Cache settings

**Requirements:**
- XDG config directory support
- Environment variable overrides
- Config validation

## Dependencies
- Click for CLI
- aiosqlite for database
- Pydantic for models
- All previous modules

## Files to Create
- `src/orion/cli.py` - Click CLI application
- `src/orion/storage/__init__.py`
- `src/orion/storage/database.py` - Database schema and operations
- `src/orion/storage/repository.py` - Result repository
- Migration scripts if needed

## Tests Required
- CLI commands execute correctly
- Argument parsing and validation
- Database CRUD operations
- Query methods return correct data
- Schema creation on first run
- Config file loading

## User Experience Goals
- Simple one-command screening: `orion run`
- Clear error messages
- Helpful output formatting
- Easy history queries
