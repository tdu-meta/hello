# Screening Orchestration Module

## Overview
Orchestrate the end-to-end screening process: fetch data, analyze indicators, evaluate strategies, find options, and send notifications.

## Topics

### 1. Stock Screener Core
Main screening engine that processes symbols through the full pipeline.

**ScreeningResult Model:**
```python
@dataclass
class ScreeningResult:
    symbol: str
    timestamp: datetime
    matches: bool
    signal_strength: float
    conditions_met: list[str]
    quote: Quote
    indicators: TechnicalIndicators
    option_recommendation: OptionContract | None
```

**StockScreener Class:**
- Initialize with DataProvider, Strategy, max_concurrent limit
- `screen_symbol(symbol)` - Screen single symbol, return ScreeningResult
- `screen_batch(symbols)` - Screen multiple symbols concurrently, yield results

**Screening Pipeline:**
1. Fetch quote for symbol
2. Fetch historical prices (1 year)
3. Calculate technical indicators
4. Evaluate strategy conditions
5. If match: fetch option chain, find best ATM put
6. Return ScreeningResult

**Requirements:**
- Async/await throughout
- Concurrent processing with semaphore (max 5 concurrent)
- Error handling per-symbol (one failure doesn't stop batch)
- Structured logging at each step

### 2. Notification Service
Send alerts when screening finds matching opportunities.

**NotificationService Class:**
- Initialize with NotificationConfig
- `send_alert(ScreeningResult)` - Send notification for match

**Email Alert Format:**
- Subject: "🎯 OFI Signal: {SYMBOL}"
- HTML body with:
  - Signal strength percentage
  - Current price
  - Conditions met list
  - Recommended option (strike, expiration, premium, IV)

**Requirements:**
- SMTP with STARTTLS
- Async email sending
- HTML formatting
- Configurable recipients

### 3. Symbol List Management
Manage the list of symbols to screen.

**Functions:**
- Load symbols from file/text
- Filter by basic criteria (exchange, market cap)
- Support S&P 500 list
- Support custom symbol lists

**Requirements:**
- File-based symbol lists
- Environment variable override
- Validation of symbol format

## Dependencies
- Data provider (YahooFinanceProvider, AlphaVantageProvider)
- Strategy engine (RuleEvaluator, OptionAnalyzer)
- Technical analysis (IndicatorCalculator)
- Notification config (SMTP settings)

## Files to Create
- `src/orion/core/__init__.py`
- `src/orion/core/screener.py` - StockScreener class
- `src/orion/notifications/__init__.py`
- `src/orion/notifications/service.py` - NotificationService class
- Symbol lists in `data/` directory

## Tests Required
- Single symbol screening (match and non-match)
- Batch screening with multiple symbols
- Concurrent limit respected
- Error handling for bad symbols
- Email formatting
- SMTP sending with mock

## Performance Requirements
- Screen 500 stocks in < 10 minutes
- Respect API rate limits
- Cache hit rate > 70%
