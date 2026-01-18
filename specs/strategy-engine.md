# Strategy Engine Module

## Overview
Parse strategy definitions and evaluate stocks against strategy criteria to identify trading opportunities.

## Topics

### 1. Strategy Parser
Parse strategy definitions from YAML files into structured objects.

**Strategy Model:**
```python
@dataclass
class Condition:
    type: str           # "trend", "oversold", "bounce"
    rule: str           # e.g., "sma_20 > sma_60"
    parameters: dict[str, Any]

@dataclass
class Strategy:
    name: str
    version: str
    description: str
    stock_criteria: dict[str, Any]
    entry_conditions: list[Condition]
    option_screening: dict[str, Any]
```

**Requirements:**
- Parse YAML files from `strategies/` directory
- Validate all required fields present
- Create typed objects from parsed data
- Handle missing/invalid fields with clear errors

### 2. Rule Evaluator
Evaluate whether a stock matches all strategy entry conditions.

**Evaluation Logic:**
- Each condition must evaluate to True
- Return: (matches: bool, conditions_met: list[str], signal_strength: float)
- Support weighted conditions for signal strength calculation

**OFI Entry Conditions:**
1. **Trend**: SMA_20 > SMA_60 (bullish trend)
2. **Oversold**: RSI < 30 within last 5 days
3. **Bounce**: Higher high + higher low pattern with volume confirmation

**Requirements:**
- Use IndicatorCalculator for technical indicators
- Use PatternDetector for pattern recognition
- Track which conditions were met
- Calculate signal strength from condition weights

### 3. Option Analyzer
Find and analyze ATM put options for OFI strategy.

**Functions:**
- `find_atm_puts()` - Find puts within 5% of current price
- `calculate_premium_yield()` - Annualized yield calculation
- `filter_by_liquidity()` - Min volume 100, min OI 500
- `find_best_opportunity()` - Highest yield liquid option

**Requirements:**
- Use OptionChain from data layer
- Sort ATM options by proximity to stock price
- Calculate annualized yield: (premium / stock_price) * (365 / days_to_exp)
- Filter by liquidity thresholds
- Return single best option or None

## Dependencies
- YAML parser (pyyaml)
- Data layer models (Quote, OptionChain, TechnicalIndicators, OHLCV)
- Technical analysis module (IndicatorCalculator, PatternDetector)

## Files to Create
- `src/orion/strategies/__init__.py`
- `src/orion/strategies/models.py` - Strategy dataclasses
- `src/orion/strategies/parser.py` - StrategyParser class
- `src/orion/strategies/evaluator.py` - RuleEvaluator class
- `src/orion/strategies/option_analyzer.py` - OptionAnalyzer class

## Tests Required
- Strategy parsing with valid/invalid YAML
- Rule evaluation for each condition type
- Signal strength calculation
- Option finding and filtering
- Yield calculation accuracy

## Existing Strategy File
- `strategies/ofi.md` - Human-readable OFI strategy definition
- Need to create `strategies/ofi.yaml` - Machine-readable version
