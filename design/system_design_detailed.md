# Stock Screener - Detailed System Design

## Overview
A stock screener system that identifies option trading opportunities based on configurable strategies, with initial focus on the OFI (Option for Income) strategy.

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Stock Screener System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Strategy   │    │    Data      │    │  Notification │  │
│  │   Engine     │───▶│   Provider   │◀───│   Service    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Screening   │    │    Cache     │    │   Alert      │  │
│  │   Rules      │    │   Manager    │    │   Manager    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Results Storage & History                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │   CLI    │          │   Cloud  │          │  Email   │
  │ Interface│          │ Scheduler│          │  Service │
  └──────────┘          └──────────┘          └──────────┘
```

## Core Components

### 1. Strategy Engine
**Responsibility**: Parse and execute trading strategies

**Key Features**:
- Strategy parser: Loads strategy definitions from markdown files
- Rule evaluator: Applies screening criteria to stock data
- Multi-strategy support: Can run multiple strategies in parallel
- Strategy versioning: Track strategy modifications over time

**Data Structures**:
```python
@dataclass
class Strategy:
    name: str
    description: str
    version: str
    screening_rules: List[ScreeningRule]
    entry_conditions: List[Condition]
    stock_criteria: StockCriteria

@dataclass
class ScreeningRule:
    rule_type: str  # 'technical', 'fundamental', 'option_chain'
    parameters: Dict[str, Any]
    weight: float
```

### 2. Data Provider
**Responsibility**: Fetch and normalize market data

**Data Sources** (Free/Low-Cost Options):
- **Stock prices**: Alpha Vantage (500 requests/day free) or Yahoo Finance
- **Options data**: Yahoo Finance or CBOE DataShop
- **Technical indicators**: Calculate locally from price data

**API Interfaces**:
```python
class DataProvider(ABC):
    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> Quote

    @abstractmethod
    async def get_option_chain(self, symbol: str, expiration: date) -> OptionChain

    @abstractmethod
    async def get_historical_prices(self, symbol: str,
                                     start: date, end: date) -> List[OHLCV]

    @abstractmethod
    async def get_technical_indicators(self, symbol: str,
                                        indicators: List[str]) -> Dict[str, float]
```

**Implementations**:
- `AlphaVantageProvider`
- `YahooFinanceProvider`
- `MockDataProvider` (for testing)

### 3. Cache Manager
**Responsibility**: Minimize API calls and improve performance

**Strategy**:
- Cache stock quotes (5-minute TTL)
- Cache option chains (15-minute TTL)
- Cache historical data (24-hour TTL)
- Persistent cache with SQLite for historical data
- In-memory cache with Redis-like TTL for live data

**Implementation**:
```python
class CacheManager:
    def __init__(self, memory_cache: Dict, persistent_cache: Database):
        self.memory = memory_cache  # e.g., cachetools.TTLCache
        self.disk = persistent_cache  # e.g., SQLite

    async def get_or_fetch(self, key: str,
                           fetch_fn: Callable,
                           ttl: int) -> Any
```

### 4. Screening Rules (OFI Strategy)
**Implementation of** [strategies/ofi.md](strategies/ofi.md)

**Technical Rules**:
1. **Bull Trend Filter**:
   - Calculate 20-week SMA and 60-week SMA
   - Require: SMA_20 > SMA_60
   - Use weekly timeframe data

2. **Oversold Condition**:
   - Calculate RSI (14-period)
   - Look for RSI < 30 (extreme selling)
   - Track recent RSI history for trend

3. **Bounce Detection**:
   - Identify recent local low
   - Confirm higher high + higher low pattern
   - Volume confirmation (volume > 20-day average)

4. **Fundamental Filter**:
   - Revenue > $1 billion annually
   - Use fundamental data API or maintain whitelist

**Option Chain Analysis**:
```python
class OptionAnalyzer:
    def find_atm_puts(self, option_chain: OptionChain,
                      current_price: float) -> List[OptionContract]:
        """Find at-the-money put options"""

    def calculate_premium_yield(self, put: OptionContract,
                                stock_price: float) -> float:
        """Calculate annualized yield from premium"""

    def filter_by_liquidity(self, options: List[OptionContract],
                           min_volume: int = 100) -> List[OptionContract]:
        """Filter out illiquid options"""
```

### 5. Notification Service
**Responsibility**: Alert users of trading opportunities

**Channels**:
- Email (primary)
- Webhook (for integrations)
- Console output (CLI mode)

**Alert Structure**:
```python
@dataclass
class Alert:
    timestamp: datetime
    strategy_name: str
    symbol: str
    signal_strength: float  # 0.0 to 1.0
    entry_conditions_met: List[str]
    recommended_action: str
    option_details: Optional[OptionRecommendation]

@dataclass
class OptionRecommendation:
    strike_price: float
    expiration: date
    premium: float
    implied_volatility: float
    delta: float
```

### 6. Results Storage
**Responsibility**: Track screening history and performance

**Database Schema** (SQLite):
```sql
-- Screening runs
CREATE TABLE screening_runs (
    id INTEGER PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    symbols_screened INTEGER,
    matches_found INTEGER,
    execution_time_ms INTEGER
);

-- Screening results
CREATE TABLE screening_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES screening_runs(id),
    symbol TEXT NOT NULL,
    signal_strength REAL,
    conditions_met TEXT,  -- JSON array
    option_data TEXT,     -- JSON object
    timestamp DATETIME
);

-- Alerts sent
CREATE TABLE alerts_sent (
    id INTEGER PRIMARY KEY,
    result_id INTEGER REFERENCES screening_results(id),
    channel TEXT,  -- 'email', 'webhook', etc.
    sent_at DATETIME,
    success BOOLEAN
);
```

## Deployment Modes

### Mode 1: CLI Terminal Execution
```bash
# Run once
python -m stock_screener run --strategy ofi

# Run with custom stock list
python -m stock_screener run --strategy ofi --symbols AAPL,MSFT,GOOGL

# Scheduled execution (using cron)
0 */2 * * * python -m stock_screener run --strategy ofi --notify email
```

### Mode 2: Cloud Service (AWS Lambda + EventBridge)
**Architecture**:
- Lambda function for screener execution
- EventBridge for scheduling (every 2 hours)
- S3 for results storage
- SES for email notifications
- Secrets Manager for API keys

**Deployment**:
```yaml
# serverless.yml or SAM template
functions:
  screener:
    handler: lambda_handler.run_screener
    timeout: 300  # 5 minutes
    memory: 512
    events:
      - schedule: rate(2 hours)
    environment:
      STRATEGY: ofi
      NOTIFICATION_EMAIL: ${env:EMAIL}
```

## Configuration Management

### Strategy Configuration (YAML)
```yaml
# strategies/ofi.yaml
name: "OFI - Option for Income"
version: "1.0.0"
description: "Grab option premium by selling ATM puts"

stock_criteria:
  min_market_cap: 1_000_000_000
  min_revenue: 1_000_000_000

technical_indicators:
  sma_20_weekly: true
  sma_60_weekly: true
  rsi_14_daily: true

entry_conditions:
  - type: "trend"
    rule: "sma_20 > sma_60"
    timeframe: "weekly"

  - type: "oversold"
    rule: "rsi < 30"
    lookback_days: 5

  - type: "bounce"
    rule: "higher_high_and_higher_low"
    confirmation: "volume_increase"

option_screening:
  moneyness: "atm"  # at-the-money
  min_days_to_expiration: 7
  max_days_to_expiration: 45
  min_premium_yield: 0.02  # 2% minimum
  min_volume: 100
```

### System Configuration
```yaml
# config.yaml
data_provider:
  primary: "alpha_vantage"
  api_key: ${ALPHA_VANTAGE_KEY}
  rate_limit: 5  # requests per minute

cache:
  quote_ttl: 300  # 5 minutes
  option_chain_ttl: 900  # 15 minutes
  historical_ttl: 86400  # 24 hours

notifications:
  email:
    enabled: true
    smtp_host: ${SMTP_HOST}
    smtp_port: 587
    from_address: ${FROM_EMAIL}
    to_addresses: ${TO_EMAILS}

  webhook:
    enabled: false
    url: ${WEBHOOK_URL}

screening:
  default_stock_universe: ["SPY_500"]  # Predefined lists
  custom_symbols: []
  max_concurrent_requests: 5

logging:
  level: "INFO"
  format: "json"
  output: "stdout"
```

## Error Handling & Resilience

### Rate Limiting
```python
class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.rpm = requests_per_minute
        self.window = deque()

    async def acquire(self):
        """Wait if necessary to respect rate limit"""
```

### Retry Strategy
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((HTTPError, TimeoutError))
)
async def fetch_with_retry(url: str) -> Dict:
    """Fetch data with exponential backoff"""
```

### Circuit Breaker
```python
class CircuitBreaker:
    """Prevent cascading failures when API is down"""
    states = ['closed', 'open', 'half_open']

    def call(self, func: Callable):
        if self.state == 'open':
            raise CircuitBreakerOpenError()
```

## Performance Considerations

### Optimization Strategies
1. **Parallel Processing**: Screen multiple stocks concurrently
2. **Batch API Calls**: Group requests where possible
3. **Incremental Updates**: Only fetch new data since last run
4. **Pre-filtering**: Apply cheap filters first (market cap, volume)
5. **Lazy Loading**: Only fetch option chains for promising candidates

### Expected Performance
- Universe: 500 stocks (S&P 500)
- Time per stock: ~2 seconds (with caching)
- Total runtime: ~3-5 minutes (with 10 parallel workers)
- API calls: ~1500 per run (quotes + option chains for ~30 candidates)

## Monitoring & Observability

### Metrics to Track
```python
@dataclass
class ScreeningMetrics:
    total_symbols_screened: int
    matches_found: int
    api_calls_made: int
    cache_hit_rate: float
    execution_time_seconds: float
    errors_encountered: int
    alerts_sent: int
```

### Logging Strategy
```python
# Structured logging
logger.info("screening_started", extra={
    "strategy": "ofi",
    "universe_size": 500,
    "timestamp": datetime.now()
})

logger.info("match_found", extra={
    "symbol": "AAPL",
    "signal_strength": 0.85,
    "conditions_met": ["trend", "oversold", "bounce"]
})
```

## Security Considerations

### API Key Management
- Store in environment variables
- Use AWS Secrets Manager in cloud deployment
- Never commit to version control
- Rotate keys periodically

### Input Validation
- Validate stock symbols against allowed characters
- Sanitize user inputs for SQL injection
- Rate limit user requests (if exposing API)

### Data Privacy
- Do not store personal trading positions
- Anonymize email addresses in logs
- Comply with data retention policies

## Testing Strategy (Detailed)

### Unit Tests
```python
# Test strategy parser
def test_strategy_parser_loads_yaml()
def test_strategy_validation()

# Test technical indicators
def test_sma_calculation()
def test_rsi_calculation()
def test_trend_detection()

# Test option analysis
def test_find_atm_puts()
def test_premium_yield_calculation()
def test_liquidity_filter()

# Test cache
def test_cache_hit()
def test_cache_expiration()
```

### Integration Tests
```python
# Test with mock data provider
def test_end_to_end_screening_with_mock_data()
def test_alert_generation()
def test_multiple_strategies_parallel()

# Test error scenarios
def test_api_failure_handling()
def test_malformed_data_handling()
```

### Performance Tests
```python
def test_screening_500_stocks_under_10_minutes()
def test_concurrent_api_calls()
def test_cache_effectiveness()
```

### Acceptance Tests
```python
# Test OFI strategy criteria
def test_ofi_bull_trend_filter()
def test_ofi_oversold_detection()
def test_ofi_bounce_pattern()
def test_ofi_fundamental_filter()
def test_ofi_end_to_end_with_historical_data()
```

## Future Enhancements

### Phase 2
- [ ] Web dashboard for viewing results
- [ ] Backtest framework to validate strategies
- [ ] Multiple strategy support simultaneously
- [ ] Machine learning for signal refinement

### Phase 3
- [ ] Paper trading integration
- [ ] Real-time screening (websocket feeds)
- [ ] Mobile app notifications
- [ ] Community strategy sharing

## Technology Stack Recommendations

### Core
- **Language**: Python 3.11+
- **Async Framework**: asyncio + aiohttp
- **Data Processing**: pandas, numpy
- **Technical Analysis**: ta-lib or pandas-ta

### Data & Storage
- **Cache**: cachetools (in-memory) + SQLite (persistent)
- **Database**: SQLite (local) or PostgreSQL (cloud)
- **Data Provider Libraries**: yfinance, alpha_vantage

### Infrastructure
- **CLI**: Click or Typer
- **Configuration**: pydantic-settings
- **Logging**: structlog
- **Testing**: pytest, pytest-asyncio, pytest-mock
- **Cloud**: AWS Lambda + EventBridge (or Azure Functions)

### Notifications
- **Email**: smtplib + email.mime (stdlib) or sendgrid
- **Monitoring**: CloudWatch (AWS) or custom logging

## Dependencies
```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
asyncio = "*"
aiohttp = "^3.9"
pandas = "^2.1"
numpy = "^1.26"
pydantic = "^2.5"
pydantic-settings = "^2.1"
click = "^8.1"
yfinance = "^0.2"
alpha-vantage = "^2.3"
pandas-ta = "^0.3"
cachetools = "^5.3"
structlog = "^24.1"
tenacity = "^8.2"  # for retries

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-asyncio = "^0.23"
pytest-mock = "^3.12"
pytest-cov = "^4.1"
black = "^23.12"
ruff = "^0.1"
mypy = "^1.8"
```
