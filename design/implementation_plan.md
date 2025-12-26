# Stock Screener - Implementation Plan

## Overview
This document provides a step-by-step implementation plan with tests for building the stock screener system. Each phase includes clear deliverables, tests to write, and success criteria.

---

## Phase 1: Foundation & Infrastructure (Week 1)

### Step 1.1: Project Setup
**Objective**: Initialize project structure and development environment

**Tasks**:
1. Create project directory structure:
   ```
   stock_screener/
   ├── src/
   │   ├── stock_screener/
   │   │   ├── __init__.py
   │   │   ├── core/
   │   │   ├── data/
   │   │   ├── strategies/
   │   │   ├── notifications/
   │   │   └── utils/
   ├── tests/
   │   ├── unit/
   │   ├── integration/
   │   └── fixtures/
   ├── strategies/
   ├── config/
   ├── pyproject.toml
   └── README.md
   ```

2. Initialize Poetry project and add dependencies
3. Setup development tools (black, ruff, mypy, pytest)
4. Create `.env.example` for configuration

**Tests to Write**:
```python
# tests/test_project_setup.py
def test_package_importable():
    """Verify package can be imported"""
    import stock_screener
    assert stock_screener.__version__

def test_config_loads():
    """Verify configuration can be loaded"""
    from stock_screener.config import load_config
    config = load_config()
    assert config is not None
```

**Success Criteria**:
- ✅ Project installs with `poetry install`
- ✅ All dev tools run without errors
- ✅ Package is importable
- ✅ Tests pass with `pytest`

---

### Step 1.2: Configuration Management
**Objective**: Implement configuration system with validation

**Tasks**:
1. Create configuration data models using Pydantic:
   ```python
   # src/stock_screener/config.py
   from pydantic_settings import BaseSettings

   class DataProviderConfig(BaseSettings):
       provider: str = "alpha_vantage"
       api_key: str
       rate_limit: int = 5

   class CacheConfig(BaseSettings):
       quote_ttl: int = 300
       option_chain_ttl: int = 900
       historical_ttl: int = 86400

   class NotificationConfig(BaseSettings):
       email_enabled: bool = True
       smtp_host: str
       smtp_port: int = 587
       from_address: str
       to_addresses: list[str]

   class Config(BaseSettings):
       data_provider: DataProviderConfig
       cache: CacheConfig
       notifications: NotificationConfig

       class Config:
           env_file = ".env"
           env_nested_delimiter = "__"
   ```

2. Implement config loader with validation
3. Create YAML config file parser
4. Setup environment variable overrides

**Tests to Write**:
```python
# tests/unit/test_config.py
def test_config_from_env():
    """Config loads from environment variables"""

def test_config_from_yaml():
    """Config loads from YAML file"""

def test_config_validation():
    """Invalid config raises validation error"""

def test_env_overrides_yaml():
    """Environment variables override YAML"""

def test_missing_required_field_fails():
    """Missing required config raises error"""
```

**Success Criteria**:
- ✅ Config loads from YAML and .env
- ✅ Validation catches invalid configs
- ✅ All config tests pass

---

### Step 1.3: Logging Infrastructure
**Objective**: Setup structured logging for observability

**Tasks**:
1. Configure structlog with JSON output
2. Create logging utilities for different log levels
3. Add correlation IDs for request tracing
4. Setup log filtering and formatting

**Implementation**:
```python
# src/stock_screener/utils/logging.py
import structlog

def setup_logging(level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
    )

logger = structlog.get_logger()
```

**Tests to Write**:
```python
# tests/unit/test_logging.py
def test_logging_outputs_json(capsys):
    """Logs are formatted as JSON"""

def test_log_level_filtering():
    """Debug logs filtered when level=INFO"""

def test_structured_context():
    """Context variables appear in logs"""
```

**Success Criteria**:
- ✅ Logs output in JSON format
- ✅ Log levels work correctly
- ✅ Structured context preserved

---

## Phase 2: Data Layer (Week 2)

### Step 2.1: Data Models
**Objective**: Define core data structures

**Tasks**:
1. Create data models for quotes, option chains, technical indicators:
   ```python
   # src/stock_screener/data/models.py
   from dataclasses import dataclass
   from datetime import date, datetime
   from decimal import Decimal

   @dataclass
   class Quote:
       symbol: str
       price: Decimal
       volume: int
       timestamp: datetime
       open: Decimal
       high: Decimal
       low: Decimal
       close: Decimal

   @dataclass
   class OptionContract:
       symbol: str
       strike: Decimal
       expiration: date
       option_type: str  # 'call' or 'put'
       bid: Decimal
       ask: Decimal
       volume: int
       open_interest: int
       implied_volatility: float
       delta: float

   @dataclass
   class OptionChain:
       symbol: str
       expiration: date
       calls: list[OptionContract]
       puts: list[OptionContract]
       underlying_price: Decimal

   @dataclass
   class OHLCV:
       timestamp: datetime
       open: Decimal
       high: Decimal
       low: Decimal
       close: Decimal
       volume: int

   @dataclass
   class TechnicalIndicators:
       symbol: str
       timestamp: datetime
       sma_20: float | None = None
       sma_60: float | None = None
       rsi_14: float | None = None
       volume_avg_20: float | None = None
   ```

**Tests to Write**:
```python
# tests/unit/test_models.py
def test_quote_creation():
    """Quote dataclass creates successfully"""

def test_option_contract_validation():
    """Option contract validates strike > 0"""

def test_option_chain_serialization():
    """OptionChain serializes to/from JSON"""

def test_ohlcv_from_dict():
    """OHLCV creates from dictionary"""
```

**Success Criteria**:
- ✅ All models create successfully
- ✅ Models serialize/deserialize correctly
- ✅ Validation works as expected

---

### Step 2.2: Data Provider Interface
**Objective**: Create abstract interface for data providers

**Tasks**:
1. Define abstract base class:
   ```python
   # src/stock_screener/data/provider.py
   from abc import ABC, abstractmethod
   from datetime import date
   from .models import Quote, OptionChain, OHLCV

   class DataProvider(ABC):
       @abstractmethod
       async def get_quote(self, symbol: str) -> Quote:
           """Get current quote for symbol"""

       @abstractmethod
       async def get_option_chain(
           self, symbol: str, expiration: date | None = None
       ) -> OptionChain:
           """Get option chain for symbol"""

       @abstractmethod
       async def get_historical_prices(
           self, symbol: str, start: date, end: date
       ) -> list[OHLCV]:
           """Get historical OHLCV data"""

       @abstractmethod
       async def get_available_expirations(
           self, symbol: str
       ) -> list[date]:
           """Get available option expiration dates"""
   ```

2. Create mock provider for testing
3. Document expected behavior and error handling

**Tests to Write**:
```python
# tests/unit/test_data_provider.py
def test_mock_provider_returns_quote():
    """Mock provider returns valid quote"""

def test_mock_provider_returns_option_chain():
    """Mock provider returns valid option chain"""

def test_invalid_symbol_raises_error():
    """Invalid symbol raises appropriate error"""

def test_historical_data_ordered_by_date():
    """Historical data returns in chronological order"""
```

**Success Criteria**:
- ✅ Interface is well-defined
- ✅ Mock provider implements all methods
- ✅ Tests pass for mock provider

---

### Step 2.3: Alpha Vantage Provider Implementation
**Objective**: Implement real data provider

**Tasks**:
1. Create Alpha Vantage client wrapper
2. Implement rate limiting
3. Add error handling and retries
4. Map API responses to internal models

**Implementation**:
```python
# src/stock_screener/data/providers/alpha_vantage.py
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from ..provider import DataProvider
from ..models import Quote, OptionChain, OHLCV

class AlphaVantageProvider(DataProvider):
    def __init__(self, api_key: str, rate_limit: int = 5):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit)
        self.base_url = "https://www.alphavantage.co/query"

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_quote(self, symbol: str) -> Quote:
        await self.rate_limiter.acquire()
        async with aiohttp.ClientSession() as session:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            async with session.get(self.base_url, params=params) as resp:
                data = await resp.json()
                return self._parse_quote(data)

    def _parse_quote(self, data: dict) -> Quote:
        # Parse API response into Quote model
        pass
```

**Tests to Write**:
```python
# tests/integration/test_alpha_vantage.py
@pytest.mark.integration
async def test_get_real_quote():
    """Fetch real quote from Alpha Vantage (requires API key)"""

@pytest.mark.integration
async def test_rate_limiting():
    """Rate limiter prevents exceeding API limits"""

def test_parse_quote_response():
    """Parse sample Alpha Vantage response correctly"""

def test_error_response_handling():
    """Handle API error responses gracefully"""

@pytest.mark.asyncio
async def test_retry_on_timeout():
    """Retries request on timeout"""
```

**Success Criteria**:
- ✅ Can fetch real quotes from API
- ✅ Rate limiting works correctly
- ✅ Errors are handled gracefully
- ✅ Retries work on failures

---

### Step 2.4: Cache Manager
**Objective**: Implement caching to reduce API calls

**Tasks**:
1. Create cache manager with TTL support:
   ```python
   # src/stock_screener/data/cache.py
   from cachetools import TTLCache
   import sqlite3
   from typing import Any, Callable

   class CacheManager:
       def __init__(self, memory_size: int = 1000):
           self.memory_cache = TTLCache(maxsize=memory_size, ttl=300)
           self.db = sqlite3.connect("cache.db")
           self._init_db()

       async def get_or_fetch(
           self,
           key: str,
           fetch_fn: Callable,
           ttl: int,
           use_disk: bool = False
       ) -> Any:
           # Check memory cache
           if key in self.memory_cache:
               logger.debug("cache_hit", key=key, cache="memory")
               return self.memory_cache[key]

           # Check disk cache if enabled
           if use_disk:
               disk_value = self._get_from_disk(key)
               if disk_value:
                   logger.debug("cache_hit", key=key, cache="disk")
                   return disk_value

           # Fetch fresh data
           logger.debug("cache_miss", key=key)
           value = await fetch_fn()

           # Store in caches
           self.memory_cache[key] = value
           if use_disk:
               self._save_to_disk(key, value, ttl)

           return value
   ```

2. Implement persistent cache with SQLite
3. Add cache invalidation methods
4. Create cache statistics tracking

**Tests to Write**:
```python
# tests/unit/test_cache.py
@pytest.mark.asyncio
async def test_cache_hit():
    """Cached value returned without calling fetch_fn"""

@pytest.mark.asyncio
async def test_cache_miss():
    """fetch_fn called on cache miss"""

@pytest.mark.asyncio
async def test_cache_expiration():
    """Expired cache entry triggers refetch"""

@pytest.mark.asyncio
async def test_disk_cache_persistence():
    """Disk cache persists across restarts"""

def test_cache_invalidation():
    """Manual invalidation removes cache entry"""

def test_cache_statistics():
    """Cache tracks hit/miss statistics"""
```

**Success Criteria**:
- ✅ Cache reduces API calls
- ✅ TTL expiration works correctly
- ✅ Disk cache persists data
- ✅ Statistics are accurate

---

## Phase 3: Technical Analysis (Week 3)

### Step 3.1: Technical Indicators Calculator
**Objective**: Implement required technical indicators

**Tasks**:
1. Create indicator calculator class:
   ```python
   # src/stock_screener/analysis/indicators.py
   import pandas as pd
   import numpy as np
   from ..data.models import OHLCV, TechnicalIndicators

   class IndicatorCalculator:
       @staticmethod
       def calculate_sma(prices: list[OHLCV], period: int) -> float:
           """Calculate Simple Moving Average"""
           if len(prices) < period:
               raise ValueError(f"Need at least {period} prices")
           closes = [p.close for p in prices[-period:]]
           return float(np.mean(closes))

       @staticmethod
       def calculate_rsi(prices: list[OHLCV], period: int = 14) -> float:
           """Calculate Relative Strength Index"""
           if len(prices) < period + 1:
               raise ValueError(f"Need at least {period + 1} prices")

           closes = pd.Series([float(p.close) for p in prices])
           delta = closes.diff()

           gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
           loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

           rs = gain / loss
           rsi = 100 - (100 / (1 + rs))
           return float(rsi.iloc[-1])

       @staticmethod
       def calculate_volume_average(
           prices: list[OHLCV], period: int
       ) -> float:
           """Calculate average volume"""
           if len(prices) < period:
               raise ValueError(f"Need at least {period} prices")
           volumes = [p.volume for p in prices[-period:]]
           return float(np.mean(volumes))

       def calculate_all(
           self, prices: list[OHLCV], symbol: str
       ) -> TechnicalIndicators:
           """Calculate all indicators"""
           return TechnicalIndicators(
               symbol=symbol,
               timestamp=prices[-1].timestamp,
               sma_20=self.calculate_sma(prices, 20),
               sma_60=self.calculate_sma(prices, 60),
               rsi_14=self.calculate_rsi(prices, 14),
               volume_avg_20=self.calculate_volume_average(prices, 20)
           )
   ```

**Tests to Write**:
```python
# tests/unit/test_indicators.py
def test_sma_calculation():
    """SMA calculates correctly with known data"""
    prices = create_test_ohlcv([10, 20, 30, 40, 50])
    sma = IndicatorCalculator.calculate_sma(prices, 5)
    assert sma == 30.0

def test_sma_insufficient_data():
    """SMA raises error with insufficient data"""
    prices = create_test_ohlcv([10, 20])
    with pytest.raises(ValueError):
        IndicatorCalculator.calculate_sma(prices, 5)

def test_rsi_calculation():
    """RSI calculates correctly"""
    prices = create_realistic_ohlcv_data()
    rsi = IndicatorCalculator.calculate_rsi(prices, 14)
    assert 0 <= rsi <= 100

def test_rsi_overbought():
    """RSI detects overbought condition"""
    prices = create_uptrend_ohlcv()
    rsi = IndicatorCalculator.calculate_rsi(prices, 14)
    assert rsi > 70

def test_rsi_oversold():
    """RSI detects oversold condition"""
    prices = create_downtrend_ohlcv()
    rsi = IndicatorCalculator.calculate_rsi(prices, 14)
    assert rsi < 30

def test_volume_average():
    """Volume average calculates correctly"""
    prices = create_test_ohlcv_with_volume()
    vol_avg = IndicatorCalculator.calculate_volume_average(prices, 20)
    assert vol_avg > 0

def test_calculate_all_indicators():
    """All indicators calculated together"""
    prices = create_sufficient_ohlcv_data(100)
    calc = IndicatorCalculator()
    indicators = calc.calculate_all(prices, "AAPL")
    assert indicators.sma_20 is not None
    assert indicators.sma_60 is not None
    assert indicators.rsi_14 is not None
```

**Success Criteria**:
- ✅ SMA calculation is accurate
- ✅ RSI calculation is accurate
- ✅ Volume averages work correctly
- ✅ All edge cases handled

---

### Step 3.2: Pattern Detection
**Objective**: Implement bounce pattern detection

**Tasks**:
1. Create pattern detector:
   ```python
   # src/stock_screener/analysis/patterns.py
   from ..data.models import OHLCV

   class PatternDetector:
       @staticmethod
       def detect_higher_high_higher_low(
           prices: list[OHLCV], lookback: int = 5
       ) -> bool:
           """Detect higher high and higher low pattern"""
           if len(prices) < lookback + 2:
               return False

           recent = prices[-lookback:]

           # Find local low and subsequent high
           local_low_idx = min(range(len(recent)),
                              key=lambda i: recent[i].low)
           if local_low_idx == len(recent) - 1:
               return False  # Low is most recent, no recovery yet

           subsequent = recent[local_low_idx + 1:]
           if len(subsequent) < 2:
               return False

           # Check for higher high and higher low
           has_higher_high = any(p.high > recent[local_low_idx].high
                                for p in subsequent)
           has_higher_low = subsequent[-1].low > recent[local_low_idx].low

           return has_higher_high and has_higher_low

       @staticmethod
       def detect_volume_increase(
           prices: list[OHLCV], threshold: float = 1.2
       ) -> bool:
           """Detect volume increase vs average"""
           if len(prices) < 21:
               return False

           avg_volume = np.mean([p.volume for p in prices[-21:-1]])
           current_volume = prices[-1].volume

           return current_volume > (avg_volume * threshold)
   ```

**Tests to Write**:
```python
# tests/unit/test_patterns.py
def test_higher_high_higher_low_detection():
    """Detects valid HHHL pattern"""
    prices = create_hhhl_pattern()
    detector = PatternDetector()
    assert detector.detect_higher_high_higher_low(prices) is True

def test_no_hhhl_in_downtrend():
    """No HHHL detected in downtrend"""
    prices = create_downtrend_ohlcv()
    detector = PatternDetector()
    assert detector.detect_higher_high_higher_low(prices) is False

def test_volume_increase_detected():
    """Detects volume spike"""
    prices = create_volume_spike_data()
    detector = PatternDetector()
    assert detector.detect_volume_increase(prices) is True

def test_normal_volume_not_flagged():
    """Normal volume not flagged as increase"""
    prices = create_normal_volume_data()
    detector = PatternDetector()
    assert detector.detect_volume_increase(prices) is False
```

**Success Criteria**:
- ✅ HHHL pattern detected correctly
- ✅ Volume spikes detected
- ✅ False positives minimized

---

## Phase 4: Strategy Engine (Week 4)

### Step 4.1: Strategy Parser
**Objective**: Parse strategy definitions from YAML/Markdown

**Tasks**:
1. Create strategy model and parser:
   ```python
   # src/stock_screener/strategies/models.py
   from dataclasses import dataclass
   from typing import Any

   @dataclass
   class Condition:
       type: str
       rule: str
       parameters: dict[str, Any]

   @dataclass
   class Strategy:
       name: str
       version: str
       description: str
       stock_criteria: dict[str, Any]
       entry_conditions: list[Condition]
       option_screening: dict[str, Any]

   # src/stock_screener/strategies/parser.py
   import yaml
   from pathlib import Path

   class StrategyParser:
       @staticmethod
       def parse_yaml(file_path: Path) -> Strategy:
           """Parse strategy from YAML file"""
           with open(file_path) as f:
               data = yaml.safe_load(f)
           return Strategy(
               name=data["name"],
               version=data["version"],
               description=data["description"],
               stock_criteria=data["stock_criteria"],
               entry_conditions=[
                   Condition(**c) for c in data["entry_conditions"]
               ],
               option_screening=data["option_screening"]
           )
   ```

**Tests to Write**:
```python
# tests/unit/test_strategy_parser.py
def test_parse_valid_strategy():
    """Parse valid strategy YAML"""
    parser = StrategyParser()
    strategy = parser.parse_yaml("tests/fixtures/ofi_strategy.yaml")
    assert strategy.name == "OFI - Option for Income"
    assert len(strategy.entry_conditions) > 0

def test_parse_invalid_yaml_raises_error():
    """Invalid YAML raises appropriate error"""
    parser = StrategyParser()
    with pytest.raises(yaml.YAMLError):
        parser.parse_yaml("tests/fixtures/invalid.yaml")

def test_missing_required_field():
    """Missing required field raises validation error"""
    # YAML missing 'name' field
    with pytest.raises(KeyError):
        parser.parse_yaml("tests/fixtures/incomplete.yaml")
```

**Success Criteria**:
- ✅ Valid strategies parse correctly
- ✅ Invalid strategies raise errors
- ✅ All fields populated

---

### Step 4.2: Rule Evaluator (OFI Strategy)
**Objective**: Implement rule evaluation logic

**Tasks**:
1. Create rule evaluator:
   ```python
   # src/stock_screener/strategies/evaluator.py
   from ..data.models import Quote, TechnicalIndicators, OHLCV
   from ..analysis.indicators import IndicatorCalculator
   from ..analysis.patterns import PatternDetector
   from .models import Strategy, Condition

   class RuleEvaluator:
       def __init__(self, strategy: Strategy):
           self.strategy = strategy
           self.indicator_calc = IndicatorCalculator()
           self.pattern_detector = PatternDetector()

       async def evaluate(
           self,
           symbol: str,
           quote: Quote,
           historical: list[OHLCV],
           indicators: TechnicalIndicators
       ) -> tuple[bool, list[str], float]:
           """
           Evaluate if symbol matches strategy criteria.

           Returns:
               (matches, conditions_met, signal_strength)
           """
           conditions_met = []
           total_weight = 0.0
           score = 0.0

           for condition in self.strategy.entry_conditions:
               weight = condition.parameters.get("weight", 1.0)
               total_weight += weight

               if self._evaluate_condition(
                   condition, symbol, quote, historical, indicators
               ):
                   conditions_met.append(condition.type)
                   score += weight

           # All conditions must be met
           matches = len(conditions_met) == len(
               self.strategy.entry_conditions
           )
           signal_strength = score / total_weight if total_weight > 0 else 0.0

           return matches, conditions_met, signal_strength

       def _evaluate_condition(
           self,
           condition: Condition,
           symbol: str,
           quote: Quote,
           historical: list[OHLCV],
           indicators: TechnicalIndicators
       ) -> bool:
           """Evaluate single condition"""
           if condition.type == "trend":
               return self._check_trend(condition, indicators)
           elif condition.type == "oversold":
               return self._check_oversold(condition, indicators, historical)
           elif condition.type == "bounce":
               return self._check_bounce(condition, historical)
           else:
               raise ValueError(f"Unknown condition type: {condition.type}")

       def _check_trend(
           self, condition: Condition, indicators: TechnicalIndicators
       ) -> bool:
           """Check trend condition (SMA_20 > SMA_60)"""
           if condition.rule == "sma_20 > sma_60":
               return (indicators.sma_20 or 0) > (indicators.sma_60 or 0)
           return False

       def _check_oversold(
           self,
           condition: Condition,
           indicators: TechnicalIndicators,
           historical: list[OHLCV]
       ) -> bool:
           """Check oversold condition (RSI < 30)"""
           if condition.rule == "rsi < 30":
               lookback = condition.parameters.get("lookback_days", 5)
               # Check if RSI was below 30 in recent history
               recent = historical[-lookback:]
               for prices in [historical[:i+1] for i in range(-lookback, 0)]:
                   if len(prices) >= 15:
                       rsi = self.indicator_calc.calculate_rsi(prices)
                       if rsi < 30:
                           return True
               return (indicators.rsi_14 or 100) < 30
           return False

       def _check_bounce(
           self, condition: Condition, historical: list[OHLCV]
       ) -> bool:
           """Check bounce pattern"""
           if condition.rule == "higher_high_and_higher_low":
               has_pattern = self.pattern_detector.detect_higher_high_higher_low(
                   historical
               )
               if condition.parameters.get("confirmation") == "volume_increase":
                   has_volume = self.pattern_detector.detect_volume_increase(
                       historical
                   )
                   return has_pattern and has_volume
               return has_pattern
           return False
   ```

**Tests to Write**:
```python
# tests/unit/test_rule_evaluator.py
@pytest.fixture
def ofi_strategy():
    return load_strategy("tests/fixtures/ofi_strategy.yaml")

@pytest.mark.asyncio
async def test_evaluate_all_conditions_met(ofi_strategy):
    """Signal generated when all conditions met"""
    evaluator = RuleEvaluator(ofi_strategy)
    # Create test data that meets all conditions
    quote, historical, indicators = create_matching_data()
    matches, conditions, strength = await evaluator.evaluate(
        "AAPL", quote, historical, indicators
    )
    assert matches is True
    assert len(conditions) == 3
    assert strength > 0.9

@pytest.mark.asyncio
async def test_evaluate_partial_match(ofi_strategy):
    """No signal when only some conditions met"""
    evaluator = RuleEvaluator(ofi_strategy)
    # Create data that only meets 2/3 conditions
    quote, historical, indicators = create_partial_match_data()
    matches, conditions, strength = await evaluator.evaluate(
        "AAPL", quote, historical, indicators
    )
    assert matches is False
    assert len(conditions) == 2

def test_check_trend_condition(ofi_strategy):
    """Trend condition evaluates correctly"""
    evaluator = RuleEvaluator(ofi_strategy)
    indicators = TechnicalIndicators(
        symbol="TEST",
        timestamp=datetime.now(),
        sma_20=150.0,
        sma_60=140.0
    )
    condition = Condition(type="trend", rule="sma_20 > sma_60", parameters={})
    assert evaluator._check_trend(condition, indicators) is True

def test_check_oversold_condition(ofi_strategy):
    """Oversold condition evaluates correctly"""
    evaluator = RuleEvaluator(ofi_strategy)
    indicators = TechnicalIndicators(
        symbol="TEST",
        timestamp=datetime.now(),
        rsi_14=25.0  # Oversold
    )
    historical = create_oversold_historical_data()
    condition = Condition(
        type="oversold",
        rule="rsi < 30",
        parameters={"lookback_days": 5}
    )
    assert evaluator._check_oversold(
        condition, indicators, historical
    ) is True

def test_check_bounce_condition(ofi_strategy):
    """Bounce condition evaluates correctly"""
    evaluator = RuleEvaluator(ofi_strategy)
    historical = create_bounce_pattern_data()
    condition = Condition(
        type="bounce",
        rule="higher_high_and_higher_low",
        parameters={"confirmation": "volume_increase"}
    )
    assert evaluator._check_bounce(condition, historical) is True
```

**Success Criteria**:
- ✅ All OFI conditions evaluate correctly
- ✅ Signal strength calculated accurately
- ✅ Partial matches handled properly

---

### Step 4.3: Option Analyzer
**Objective**: Find and analyze ATM put options

**Tasks**:
1. Implement option analysis:
   ```python
   # src/stock_screener/strategies/option_analyzer.py
   from ..data.models import OptionChain, OptionContract
   from decimal import Decimal
   from datetime import date, timedelta

   class OptionAnalyzer:
       def find_atm_puts(
           self,
           option_chain: OptionChain,
           tolerance: float = 0.05
       ) -> list[OptionContract]:
           """Find at-the-money put options"""
           underlying = float(option_chain.underlying_price)
           lower_bound = underlying * (1 - tolerance)
           upper_bound = underlying * (1 + tolerance)

           atm_puts = [
               put for put in option_chain.puts
               if lower_bound <= float(put.strike) <= upper_bound
           ]

           return sorted(atm_puts, key=lambda p: abs(
               float(p.strike) - underlying
           ))

       def calculate_premium_yield(
           self,
           put: OptionContract,
           stock_price: Decimal,
           expiration: date
       ) -> float:
           """Calculate annualized premium yield"""
           premium = (float(put.bid) + float(put.ask)) / 2
           days_to_exp = (expiration - date.today()).days

           if days_to_exp <= 0:
               return 0.0

           yield_per_day = premium / float(stock_price)
           annualized_yield = yield_per_day * (365 / days_to_exp)

           return annualized_yield

       def filter_by_liquidity(
           self,
           options: list[OptionContract],
           min_volume: int = 100,
           min_open_interest: int = 500
       ) -> list[OptionContract]:
           """Filter out illiquid options"""
           return [
               opt for opt in options
               if opt.volume >= min_volume
               and opt.open_interest >= min_open_interest
           ]

       def find_best_opportunity(
           self,
           option_chain: OptionChain,
           min_yield: float = 0.02,
           min_volume: int = 100
       ) -> OptionContract | None:
           """Find best option opportunity"""
           atm_puts = self.find_atm_puts(option_chain)
           liquid_puts = self.filter_by_liquidity(atm_puts, min_volume)

           best_put = None
           best_yield = 0.0

           for put in liquid_puts:
               yield_val = self.calculate_premium_yield(
                   put,
                   option_chain.underlying_price,
                   put.expiration
               )

               if yield_val >= min_yield and yield_val > best_yield:
                   best_yield = yield_val
                   best_put = put

           return best_put
   ```

**Tests to Write**:
```python
# tests/unit/test_option_analyzer.py
def test_find_atm_puts():
    """Find ATM puts within tolerance"""
    chain = create_option_chain(underlying_price=100.0)
    analyzer = OptionAnalyzer()
    atm_puts = analyzer.find_atm_puts(chain, tolerance=0.05)

    assert len(atm_puts) > 0
    for put in atm_puts:
        assert 95.0 <= float(put.strike) <= 105.0

def test_calculate_premium_yield():
    """Premium yield calculates correctly"""
    put = create_option_contract(
        strike=100.0, bid=2.0, ask=2.1, expiration_days=30
    )
    analyzer = OptionAnalyzer()
    yield_val = analyzer.calculate_premium_yield(
        put, Decimal("100.0"), date.today() + timedelta(days=30)
    )

    # ~2% premium over 30 days = ~24% annualized
    assert 0.20 <= yield_val <= 0.30

def test_filter_by_liquidity():
    """Filters out illiquid options"""
    options = [
        create_option_contract(volume=50, open_interest=200),  # Illiquid
        create_option_contract(volume=500, open_interest=1000),  # Liquid
    ]
    analyzer = OptionAnalyzer()
    liquid = analyzer.filter_by_liquidity(options, min_volume=100)

    assert len(liquid) == 1
    assert liquid[0].volume == 500

def test_find_best_opportunity():
    """Finds highest yield liquid option"""
    chain = create_option_chain_with_varying_yields()
    analyzer = OptionAnalyzer()
    best = analyzer.find_best_opportunity(chain, min_yield=0.02)

    assert best is not None
    assert best.volume >= 100
```

**Success Criteria**:
- ✅ ATM options identified correctly
- ✅ Yield calculations accurate
- ✅ Liquidity filtering works
- ✅ Best option selected properly

---

## Phase 5: Screening Orchestration (Week 5)

### Step 5.1: Stock Screener Core
**Objective**: Orchestrate the screening process

**Tasks**:
1. Create main screener class:
   ```python
   # src/stock_screener/core/screener.py
   import asyncio
   from typing import AsyncIterator
   from ..data.provider import DataProvider
   from ..strategies.models import Strategy
   from ..strategies.evaluator import RuleEvaluator
   from ..strategies.option_analyzer import OptionAnalyzer

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

   class StockScreener:
       def __init__(
           self,
           data_provider: DataProvider,
           strategy: Strategy,
           max_concurrent: int = 5
       ):
           self.provider = data_provider
           self.strategy = strategy
           self.evaluator = RuleEvaluator(strategy)
           self.option_analyzer = OptionAnalyzer()
           self.semaphore = asyncio.Semaphore(max_concurrent)

       async def screen_symbol(self, symbol: str) -> ScreeningResult:
           """Screen a single symbol"""
           async with self.semaphore:
               logger.info("screening_symbol", symbol=symbol)

               # Fetch data
               quote = await self.provider.get_quote(symbol)
               historical = await self.provider.get_historical_prices(
                   symbol,
                   start=date.today() - timedelta(days=365),
                   end=date.today()
               )

               # Calculate indicators
               calc = IndicatorCalculator()
               indicators = calc.calculate_all(historical, symbol)

               # Evaluate strategy
               matches, conditions, strength = await self.evaluator.evaluate(
                   symbol, quote, historical, indicators
               )

               # Analyze options if match
               option_rec = None
               if matches:
                   option_chain = await self.provider.get_option_chain(symbol)
                   option_rec = self.option_analyzer.find_best_opportunity(
                       option_chain,
                       min_yield=self.strategy.option_screening["min_premium_yield"]
                   )

               return ScreeningResult(
                   symbol=symbol,
                   timestamp=datetime.now(),
                   matches=matches,
                   signal_strength=strength,
                   conditions_met=conditions,
                   quote=quote,
                   indicators=indicators,
                   option_recommendation=option_rec
               )

       async def screen_batch(
           self, symbols: list[str]
       ) -> AsyncIterator[ScreeningResult]:
           """Screen multiple symbols concurrently"""
           tasks = [self.screen_symbol(sym) for sym in symbols]

           for coro in asyncio.as_completed(tasks):
               try:
                   result = await coro
                   yield result
               except Exception as e:
                   logger.error("screening_error", error=str(e))
   ```

**Tests to Write**:
```python
# tests/integration/test_screener.py
@pytest.mark.asyncio
async def test_screen_single_symbol(mock_provider, ofi_strategy):
    """Screen single symbol successfully"""
    screener = StockScreener(mock_provider, ofi_strategy)
    result = await screener.screen_symbol("AAPL")

    assert result.symbol == "AAPL"
    assert result.signal_strength >= 0.0

@pytest.mark.asyncio
async def test_screen_matching_symbol(mock_provider, ofi_strategy):
    """Matching symbol returns option recommendation"""
    mock_provider.set_matching_data("MSFT")
    screener = StockScreener(mock_provider, ofi_strategy)
    result = await screener.screen_symbol("MSFT")

    assert result.matches is True
    assert result.option_recommendation is not None

@pytest.mark.asyncio
async def test_screen_batch(mock_provider, ofi_strategy):
    """Screen multiple symbols concurrently"""
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    screener = StockScreener(mock_provider, ofi_strategy)

    results = []
    async for result in screener.screen_batch(symbols):
        results.append(result)

    assert len(results) == 4

@pytest.mark.asyncio
async def test_concurrent_limit_respected(mock_provider, ofi_strategy):
    """Respects max concurrent requests"""
    screener = StockScreener(mock_provider, ofi_strategy, max_concurrent=2)
    # Test that no more than 2 requests happen simultaneously
```

**Success Criteria**:
- ✅ Single symbol screening works
- ✅ Batch screening completes successfully
- ✅ Concurrency limits respected
- ✅ Errors handled gracefully

---

### Step 5.2: Notification Service
**Objective**: Send alerts for trading opportunities

**Tasks**:
1. Create notification service:
   ```python
   # src/stock_screener/notifications/service.py
   import smtplib
   from email.mime.text import MIMEText
   from email.mime.multipart import MIMEMultipart
   from ..core.screener import ScreeningResult

   class NotificationService:
       def __init__(self, config: NotificationConfig):
           self.config = config

       async def send_alert(self, result: ScreeningResult):
           """Send alert for screening result"""
           if self.config.email_enabled:
               await self._send_email(result)

       async def _send_email(self, result: ScreeningResult):
           """Send email notification"""
           subject = f"🎯 OFI Signal: {result.symbol}"
           body = self._format_email_body(result)

           msg = MIMEMultipart()
           msg["From"] = self.config.from_address
           msg["To"] = ", ".join(self.config.to_addresses)
           msg["Subject"] = subject

           msg.attach(MIMEText(body, "html"))

           with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
               server.starttls()
               if self.config.smtp_password:
                   server.login(self.config.smtp_user, self.config.smtp_password)
               server.send_message(msg)

           logger.info("alert_sent", symbol=result.symbol, channel="email")

       def _format_email_body(self, result: ScreeningResult) -> str:
           """Format HTML email body"""
           opt = result.option_recommendation
           return f"""
           <html>
             <body>
               <h2>OFI Signal: {result.symbol}</h2>
               <p><strong>Signal Strength:</strong> {result.signal_strength:.0%}</p>
               <p><strong>Current Price:</strong> ${result.quote.price}</p>

               <h3>Conditions Met:</h3>
               <ul>
                 {''.join(f"<li>{c}</li>" for c in result.conditions_met)}
               </ul>

               {self._format_option_details(opt) if opt else ""}

               <p><em>Generated at {result.timestamp}</em></p>
             </body>
           </html>
           """

       def _format_option_details(self, option: OptionContract) -> str:
           return f"""
           <h3>Recommended Put Option:</h3>
           <ul>
             <li>Strike: ${option.strike}</li>
             <li>Expiration: {option.expiration}</li>
             <li>Premium: ${(option.bid + option.ask) / 2:.2f}</li>
             <li>IV: {option.implied_volatility:.1%}</li>
           </ul>
           """
   ```

**Tests to Write**:
```python
# tests/unit/test_notifications.py
@pytest.mark.asyncio
async def test_send_email_alert(mock_smtp):
    """Email alert sends successfully"""
    config = NotificationConfig(
        email_enabled=True,
        smtp_host="localhost",
        smtp_port=587,
        from_address="test@example.com",
        to_addresses=["user@example.com"]
    )
    service = NotificationService(config)
    result = create_matching_result()

    await service.send_alert(result)

    assert mock_smtp.send_called
    assert result.symbol in mock_smtp.sent_message

def test_format_email_body():
    """Email body formats correctly"""
    service = NotificationService(test_config)
    result = create_matching_result()
    body = service._format_email_body(result)

    assert result.symbol in body
    assert "Signal Strength" in body
    assert all(c in body for c in result.conditions_met)
```

**Success Criteria**:
- ✅ Email alerts send successfully
- ✅ HTML formatting is correct
- ✅ All result data included

---

## Phase 6: CLI & Storage (Week 6)

### Step 6.1: Results Storage
**Objective**: Persist screening results

**Tasks**:
1. Implement database layer (see system design for schema)
2. Create repository for CRUD operations
3. Add result history tracking

**Tests to Write**:
```python
# tests/integration/test_storage.py
def test_save_screening_run():
    """Save screening run to database"""

def test_save_screening_results():
    """Save individual results"""

def test_query_results_by_symbol():
    """Query results for specific symbol"""

def test_query_results_by_date_range():
    """Query results within date range"""
```

---

### Step 6.2: CLI Interface
**Objective**: Create command-line interface

**Tasks**:
1. Create CLI with Click:
   ```python
   # src/stock_screener/cli.py
   import click
   from .core.screener import StockScreener
   from .strategies.parser import StrategyParser

   @click.group()
   def cli():
       """Stock Screener CLI"""
       pass

   @cli.command()
   @click.option("--strategy", required=True, help="Strategy file path")
   @click.option("--symbols", help="Comma-separated symbols")
   @click.option("--notify/--no-notify", default=False)
   async def run(strategy: str, symbols: str, notify: bool):
       """Run screening"""
       # Implementation
       pass

   @cli.command()
   @click.argument("symbol")
   def history(symbol: str):
       """View screening history for symbol"""
       # Implementation
       pass
   ```

**Tests to Write**:
```python
# tests/integration/test_cli.py
def test_cli_run_command():
    """CLI run command executes"""

def test_cli_with_custom_symbols():
    """CLI accepts custom symbol list"""

def test_cli_history_command():
    """CLI history command displays results"""
```

---

## Phase 7: Cloud Deployment (Week 7)

### Step 7.1: Lambda Function
**Objective**: Deploy as AWS Lambda

**Tasks**:
1. Create Lambda handler
2. Setup environment variables
3. Configure EventBridge schedule
4. Test deployment

**Tests to Write**:
```python
# tests/deployment/test_lambda.py
def test_lambda_handler():
    """Lambda handler processes event"""

def test_lambda_timeout_handling():
    """Lambda handles timeout gracefully"""
```

---

## Testing Strategy Summary

### Test Coverage Goals
- **Unit tests**: 80%+ coverage
- **Integration tests**: All critical paths
- **End-to-end tests**: Complete screening workflow

### Test Fixtures
Create reusable fixtures in `tests/fixtures/`:
- Sample OHLCV data
- Mock API responses
- Strategy YAML files
- Option chain data

### Continuous Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=stock_screener --cov-report=html

# Run specific test types
pytest tests/unit
pytest tests/integration

# Run tests matching pattern
pytest -k "test_ofi"
```

---

## Success Metrics

### Functional Requirements
- ✅ Successfully screens S&P 500 stocks
- ✅ Identifies OFI opportunities accurately
- ✅ Sends email alerts within 5 minutes
- ✅ Runs every 2 hours without manual intervention

### Performance Requirements
- ✅ Screen 500 stocks in < 10 minutes
- ✅ API rate limits respected
- ✅ Cache hit rate > 70%
- ✅ Zero crashes in 30-day period

### Quality Requirements
- ✅ Test coverage > 80%
- ✅ All linting checks pass
- ✅ Type checking with mypy passes
- ✅ No critical security vulnerabilities

---

## Risk Mitigation

### Risk: API Rate Limiting
**Mitigation**: Implement aggressive caching, rate limiter, retry logic

### Risk: Data Quality Issues
**Mitigation**: Validate all API responses, log anomalies, fallback data sources

### Risk: False Signals
**Mitigation**: Backtesting framework, signal strength scoring, conservative thresholds

### Risk: Deployment Failures
**Mitigation**: Comprehensive testing, canary deployments, rollback procedures
