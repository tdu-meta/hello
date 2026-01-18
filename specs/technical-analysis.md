# Technical Analysis Module

## Overview
Implement technical indicators and pattern detection for identifying trading opportunities in the Option for Income (OFI) strategy.

## Topics

### 1. Indicator Calculator
Calculate technical indicators from historical OHLCV data:

**Required Indicators:**
- Simple Moving Average (SMA) - 20 and 60 period
- Relative Strength Index (RSI) - 14 period
- Volume Average - 20 period

**Requirements:**
- Accept list of OHLCV objects as input
- Return TechnicalIndicators dataclass with all calculated values
- Handle edge cases: insufficient data, empty lists
- Use pandas-ta library for efficient calculations

### 2. Pattern Detection
Detect chart patterns for OFI entry signals:

**Bounce Pattern (Higher High + Higher Low):**
- Detect local low within lookback period (default 5 bars)
- Verify subsequent high exceeds previous high
- Verify current low exceeds previous low
- Returns boolean indicating pattern presence

**Volume Confirmation:**
- Compare current volume to 20-day average
- Threshold: 1.2x average volume
- Returns boolean for volume spike detection

**Requirements:**
- Accept list of OHLCV objects
- Configurable lookback periods
- Configurable thresholds
- Return boolean results

### 3. Data Models
Extend existing data models in `src/orion/data/models.py`:

**TechnicalIndicators (already exists):**
- symbol: str
- timestamp: datetime
- sma_20: float | None
- sma_60: float | None
- rsi_14: float | None
- volume_avg_20: float | None

## Dependencies
- pandas-ta for indicator calculations
- Existing OHLCV models from data layer

## Files to Create
- `src/orion/analysis/__init__.py`
- `src/orion/analysis/indicators.py` - IndicatorCalculator class
- `src/orion/analysis/patterns.py` - PatternDetector class

## Tests Required
- Unit tests for each indicator calculation
- Unit tests for pattern detection
- Edge case handling (insufficient data, empty inputs)
- Integration tests with real OHLCV data
