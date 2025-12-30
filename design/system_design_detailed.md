# Orion - Detailed System Design

## Overview
Orion is a trading signals platform that identifies option trading opportunities based on configurable strategies. Named after the legendary hunter of Greek mythology, Orion tracks down market opportunities with precision and efficiency.

The platform consists of two main subsystems:
1. **Screener**: Weekly curation of tradable stocks based on fundamentals (revenue, volume, liquidity)
2. **Detector**: Real-time or on-demand detection of trading opportunities via technical analysis

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orion Platform                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │               SCREENER (Weekly Workflow)               │     │
│  │  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │     │
│  │  │  External    │───▶│   Ranking    │───▶│  Top N  │ │     │
│  │  │  Screener    │    │   Engine     │    │ Stocks  │ │     │
│  │  │  Service     │    │              │    │ (N=50)  │ │     │
│  │  └──────────────┘    └──────────────┘    └─────────┘ │     │
│  │         │                     │                 │      │     │
│  │         └─────────────────────┴─────────────────┘      │     │
│  │                            ▼                            │     │
│  │                  ┌──────────────────┐                  │     │
│  │                  │  Watchlist DB    │                  │     │
│  │                  │  (Curated List)  │                  │     │
│  │                  └──────────────────┘                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │             DETECTOR (On-Demand/Live Service)          │     │
│  │  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │     │
│  │  │  Technical   │    │    Pattern   │    │ Signal  │ │     │
│  │  │  Indicators  │───▶│   Detection  │───▶│Generator│ │     │
│  │  │  (SMA, RSI)  │    │   (HHHL)     │    │         │ │     │
│  │  └──────────────┘    └──────────────┘    └─────────┘ │     │
│  │         │                     │                 │      │     │
│  │         └─────────────────────┴─────────────────┘      │     │
│  │                            ▼                            │     │
│  │                  ┌──────────────────┐                  │     │
│  │                  │ Notification     │                  │     │
│  │                  │ Service (Email)  │                  │     │
│  │                  └──────────────────┘                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                   Shared Services                      │     │
│  │  ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │     │
│  │  │    Data      │    │    Cache     │    │ Results │ │     │
│  │  │  Providers   │    │   Manager    │    │ Storage │ │     │
│  │  └──────────────┘    └──────────────┘    └─────────┘ │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
           │                      │                      │
           ▼                      ▼                      ▼
    ┌──────────┐         ┌──────────────┐        ┌──────────┐
    │   CLI    │         │   Prefect    │        │  Email   │
    │  (Local) │         │ (Workflows)  │        │ Service  │
    └──────────┘         └──────────────┘        └──────────┘
```

## System Workflows

### Screener Workflow (Weekly)
**Schedule**: Runs every Sunday at 8 PM
**Duration**: ~30-60 minutes
**Purpose**: Curate a watchlist of top N stocks for trading

**Steps**:
1. **External Screener Query**: Query external screener service with fundamental criteria
2. **Rank & Score**: Apply ranking algorithm to score stocks
3. **Select Top N**: Keep only top 50 stocks
4. **Update Watchlist**: Persist to database
5. **Notify**: Send weekly summary email

### Detector Workflow (On-Demand/Live)
**Trigger**: CLI command or continuous service
**Frequency**: On-demand or real-time monitoring
**Purpose**: Detect trading opportunities in watchlist stocks

**Steps**:
1. **Load Watchlist**: Get current top N stocks from database
2. **Fetch Market Data**: Get latest prices, option chains
3. **Technical Analysis**: Calculate indicators (SMA, RSI, patterns)
4. **Signal Generation**: Identify opportunities matching criteria
5. **Alert**: Send email notifications for matches

## Core Components

### 1. External Screener Service Integration
**Responsibility**: Query external stock screeners for fundamental filtering

**Recommended Services**:
- **Finviz** (Free tier available)
  - Filters: Market cap, volume, revenue, industry
  - Export: CSV/table scraping
  - Limits: ~5000 stocks in universe

- **Stock Rover** (API available)
  - Advanced fundamental screening
  - Custom metrics and ratios
  - Paid tier required for API

- **Yahoo Finance Screener** (Free)
  - Basic fundamental filters
  - Large stock universe
  - Can scrape results

- **Alpha Vantage Fundamentals API** (Free tier: 500 calls/day)
  - Company overview, financials
  - Programmatic access
  - Need to build own filtering

**Implementation**:
```python
class ExternalScreener(ABC):
    @abstractmethod
    async def screen(self, criteria: ScreeningCriteria) -> List[StockCandidate]:
        """Query external screener with criteria"""

@dataclass
class ScreeningCriteria:
    min_market_cap: float  # e.g., 1B
    min_volume: int  # e.g., 1M shares/day
    min_revenue: float  # e.g., 1B annually
    max_results: int = 200
    industries: List[str] = None

@dataclass
class StockCandidate:
    symbol: str
    company_name: str
    market_cap: float
    volume: int
    revenue: float
    score: float = 0.0  # Added by ranking engine
```

### 2. Ranking Engine
**Responsibility**: Score and rank stock candidates to select top N

**Ranking Criteria**:
1. **Option Liquidity** (40% weight)
   - Open interest > 500
   - Bid-ask spread < 5%
   - Multiple expirations available

2. **Financial Health** (30% weight)
   - Revenue growth YoY
   - Positive free cash flow
   - Debt-to-equity ratio

3. **Volume & Liquidity** (20% weight)
   - Average daily volume > 1M
   - Consistent volume (low variance)

4. **Technical Setup** (10% weight)
   - Above 200-day SMA
   - Not in downtrend

**Implementation**:
```python
class RankingEngine:
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights

    async def rank_stocks(
        self,
        candidates: List[StockCandidate],
        top_n: int = 50
    ) -> List[RankedStock]:
        """Score and rank stocks, return top N"""
        scored = []
        for candidate in candidates:
            score = await self._calculate_score(candidate)
            scored.append(RankedStock(
                symbol=candidate.symbol,
                score=score,
                metrics=self._get_metrics(candidate)
            ))

        # Sort by score descending
        ranked = sorted(scored, key=lambda x: x.score, reverse=True)
        return ranked[:top_n]

    async def _calculate_score(self, candidate: StockCandidate) -> float:
        """Calculate weighted score"""
        option_score = await self._score_option_liquidity(candidate.symbol)
        financial_score = self._score_financials(candidate)
        volume_score = self._score_volume(candidate)
        technical_score = await self._score_technical(candidate.symbol)

        total = (
            option_score * self.weights['option_liquidity'] +
            financial_score * self.weights['financial_health'] +
            volume_score * self.weights['volume'] +
            technical_score * self.weights['technical']
        )
        return total

@dataclass
class RankedStock:
    symbol: str
    score: float
    rank: int = 0
    metrics: Dict[str, Any] = None
    added_date: date = None
```

### 3. Watchlist Database
**Responsibility**: Store and manage curated stock list

**Schema**:
```sql
-- Current watchlist (top N stocks)
CREATE TABLE watchlist (
    symbol TEXT PRIMARY KEY,
    rank INTEGER NOT NULL,
    score REAL NOT NULL,
    added_date DATE NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metrics JSON  -- Store ranking metrics
);

-- Historical watchlist for tracking
CREATE TABLE watchlist_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    rank INTEGER,
    score REAL,
    week_start DATE NOT NULL,
    week_end DATE,
    UNIQUE(symbol, week_start)
);

-- Weekly screening runs
CREATE TABLE screening_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_candidates INTEGER,
    top_n_selected INTEGER,
    criteria JSON,
    execution_time_ms INTEGER
);
```

**Operations**:
```python
class WatchlistManager:
    async def update_watchlist(
        self,
        ranked_stocks: List[RankedStock]
    ):
        """Replace watchlist with new top N stocks"""
        # Archive old watchlist to history
        await self._archive_current()

        # Insert new watchlist
        for i, stock in enumerate(ranked_stocks, 1):
            stock.rank = i
            await self._insert_stock(stock)

    async def get_current_watchlist(self) -> List[RankedStock]:
        """Get current top N stocks"""
        return await self.db.query(
            "SELECT * FROM watchlist ORDER BY rank"
        )

    async def get_watchlist_for_detection(self) -> List[str]:
        """Get symbols for detector workflow"""
        return [s.symbol for s in await self.get_current_watchlist()]
```

### 4. Strategy Engine
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

### Mode 1: CLI Execution (On-Demand)
```bash
# Run screener workflow manually
orion screen --top-n 50

# Run detector on current watchlist
orion detect --strategy ofi

# Run detector on specific symbols
orion detect --strategy ofi --symbols AAPL,MSFT

# Get current watchlist
orion watchlist --show
```

### Mode 2: Prefect Workflows (Cloud/Scheduled)

**Why Prefect?**
- Modern workflow orchestration (better than Airflow/cron)
- Built-in scheduling, retries, and error handling
- Easy local development and cloud deployment
- Excellent observability and monitoring
- Free cloud tier available

**Architecture**:
```python
# workflows/screener_flow.py
from prefect import flow, task
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

@task(retries=3, retry_delay_seconds=60)
async def query_external_screener():
    """Query Finviz/Yahoo for stock candidates"""
    screener = FinvizScreener()
    return await screener.screen(criteria)

@task
async def rank_and_select_top_n(candidates, n=50):
    """Rank candidates and select top N"""
    ranker = RankingEngine(weights)
    return await ranker.rank_stocks(candidates, top_n=n)

@task
async def update_watchlist(ranked_stocks):
    """Persist top N to database"""
    manager = WatchlistManager()
    await manager.update_watchlist(ranked_stocks)

@task
async def send_weekly_summary(watchlist):
    """Email weekly watchlist summary"""
    notifier = NotificationService()
    await notifier.send_watchlist_summary(watchlist)

@flow(name="Weekly Screener")
async def screener_workflow(top_n: int = 50):
    """Weekly screener workflow"""
    logger.info("Starting weekly screener workflow")

    # Step 1: Query external screener
    candidates = await query_external_screener()
    logger.info(f"Found {len(candidates)} candidates")

    # Step 2: Rank and select top N
    ranked = await rank_and_select_top_n(candidates, n=top_n)
    logger.info(f"Selected top {len(ranked)} stocks")

    # Step 3: Update watchlist
    await update_watchlist(ranked)

    # Step 4: Send summary
    await send_weekly_summary(ranked)

    return ranked

# Deployment configuration
deployment = Deployment.build_from_flow(
    flow=screener_workflow,
    name="weekly-screener",
    schedule=CronSchedule(cron="0 20 * * 0"),  # Sunday 8 PM
    work_queue_name="orion-queue",
    parameters={"top_n": 50}
)
```

**Detector Flow**:
```python
# workflows/detector_flow.py
@task(retries=2)
async def load_watchlist():
    """Load current watchlist from DB"""
    manager = WatchlistManager()
    return await manager.get_watchlist_for_detection()

@task
async def fetch_market_data(symbols):
    """Fetch latest prices and option chains"""
    provider = AlphaVantageProvider()
    return await provider.batch_get_quotes(symbols)

@task
async def detect_signals(market_data, strategy):
    """Run technical analysis and detect signals"""
    detector = SignalDetector(strategy)
    return await detector.scan_for_signals(market_data)

@task
async def send_alerts(signals):
    """Send email alerts for detected opportunities"""
    notifier = NotificationService()
    for signal in signals:
        await notifier.send_signal_alert(signal)

@flow(name="Signal Detector")
async def detector_workflow(strategy_name: str = "ofi"):
    """On-demand or live signal detection"""
    logger.info(f"Running detector with strategy: {strategy_name}")

    # Load strategy and watchlist
    strategy = load_strategy(strategy_name)
    symbols = await load_watchlist()

    # Fetch market data
    market_data = await fetch_market_data(symbols)

    # Detect signals
    signals = await detect_signals(market_data, strategy)
    logger.info(f"Detected {len(signals)} signals")

    # Send alerts
    if signals:
        await send_alerts(signals)

    return signals

# Can run on-demand via CLI or schedule
# For live monitoring: schedule every 15 minutes during market hours
detector_deployment = Deployment.build_from_flow(
    flow=detector_workflow,
    name="live-detector",
    schedule=CronSchedule(
        cron="*/15 9-16 * * 1-5",  # Every 15 min, 9am-4pm, Mon-Fri
        timezone="America/New_York"
    ),
    work_queue_name="orion-queue",
    parameters={"strategy_name": "ofi"}
)
```

**Local Development**:
```bash
# Start Prefect server locally
prefect server start

# Deploy flows
python workflows/screener_flow.py
python workflows/detector_flow.py

# Run manually
prefect deployment run 'Weekly Screener/weekly-screener'
prefect deployment run 'Signal Detector/live-detector'
```

**Cloud Deployment** (Prefect Cloud):
```bash
# Login to Prefect Cloud (free tier)
prefect cloud login

# Create work pool
prefect work-pool create orion-pool --type process

# Deploy workflows
prefect deploy workflows/screener_flow.py:screener_workflow
prefect deploy workflows/detector_flow.py:detector_workflow

# Start worker (can run on any server/container)
prefect worker start --pool orion-pool
```

**Alternative: Self-Hosted on VPS**:
- Run Prefect server on DigitalOcean droplet ($6/month)
- SQLite for Prefect metadata
- PostgreSQL for Orion data
- Systemd for worker process management

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
- **Package Name**: orion
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
