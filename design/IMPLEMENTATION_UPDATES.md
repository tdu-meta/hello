# Implementation Plan Updates for Screener/Detector Architecture

## Key Changes from Original Plan

### Architecture Changes
1. **Separation of Concerns**: Split into two distinct workflows
   - **Screener**: Weekly curation (runs Sunday 8 PM)
   - **Detector**: On-demand/live monitoring (runs as needed)

2. **External Dependencies**: Use existing screener services instead of building from scratch
   - Finviz (preferred - free tier)
   - Yahoo Finance Screener
   - Alpha Vantage Fundamentals API

3. **Workflow Orchestration**: Use Prefect instead of AWS Lambda + EventBridge
   - Better developer experience
   - Built-in retries and error handling
   - Free cloud tier available

4. **Watchlist Management**: Top N (50) stock curation
   - Ranking engine with weighted scoring
   - Historical tracking
   - Weekly refresh

### Updated Phase Priorities

## PHASE 1: Foundation & External Integrations (Week 1-2)

### 1.1 Project Setup (Same as before)
- Initialize Poetry project
- Setup dev tools (black, ruff, mypy, pytest)
- Configuration management with Pydantic

### 1.2 External Screener Integration (NEW)
**Objective**: Connect to Finviz/Yahoo for fundamental screening

**Tasks**:
1. Research and choose primary screener service
2. Implement Finviz scraper:
   ```python
   # src/orion/screeners/finviz.py
   class FinvizScreener:
       async def screen(self, criteria: ScreeningCriteria) -> List[StockCandidate]:
           """Scrape Finviz with filters"""
           url = self._build_url(criteria)
           html = await self._fetch(url)
           return self._parse_results(html)
   ```

3. Implement Yahoo Finance screener as backup
4. Add rate limiting and error handling

**Tests**:
```python
def test_finviz_screen_returns_candidates()
def test_yahoo_screen_returns_candidates()
def test_screener_respects_criteria()
def test_screener_handles_errors()
```

**Success Criteria**:
- ✅ Can query Finviz with market cap, volume, revenue filters
- ✅ Returns 100+ stock candidates
- ✅ Handles network errors gracefully

### 1.3 Watchlist Database (NEW)
**Objective**: Create database for storing curated watchlist

**Tasks**:
1. Design schema (watchlist, watchlist_history, screening_runs)
2. Implement WatchlistManager class
3. Add CRUD operations
4. Implement archival/history tracking

**Tests**:
```python
def test_create_watchlist()
def test_update_watchlist_archives_old()
def test_get_current_watchlist()
def test_watchlist_history_tracking()
```

## PHASE 2: Ranking Engine (Week 3)

### 2.1 Ranking Algorithm
**Objective**: Score and rank stock candidates

**Tasks**:
1. Implement scoring for each criterion:
   - Option liquidity (40%)
   - Financial health (30%)
   - Volume/liquidity (20%)
   - Technical setup (10%)

2. Combine scores with weighted average
3. Sort and select top N

**Tests**:
```python
def test_option_liquidity_scoring()
def test_financial_health_scoring()
def test_volume_scoring()
def test_technical_scoring()
def test_rank_stocks_returns_top_n()
def test_ranking_is_deterministic()
```

### 2.2 Data Collection for Ranking
**Objective**: Gather data needed for ranking

**Tasks**:
1. Fetch option chains for candidates
2. Get financial data (revenue, FCF, debt)
3. Calculate technical indicators (200-day SMA)
4. Assess volume consistency

## PHASE 3: Screener Workflow (Week 4)

### 3.1 Prefect Screener Flow
**Objective**: Create weekly screener workflow

**Tasks**:
1. Define Prefect tasks:
   - query_external_screener
   - rank_and_select_top_n
   - update_watchlist
   - send_weekly_summary

2. Create screener flow
3. Add error handling and retries
4. Configure scheduling (Sunday 8 PM)

**Tests**:
```python
@pytest.mark.integration
async def test_screener_flow_end_to_end()

async def test_screener_handles_external_service_failure()
async def test_screener_updates_watchlist()
async def test_screener_sends_summary_email()
```

## PHASE 4: Detector Workflow (Week 5)

### 4.1 Signal Detection Engine (MODIFIED)
**Objective**: Detect trading signals in watchlist stocks

**Tasks**:
1. Load watchlist from database
2. Fetch market data for watchlist stocks only
3. Run technical analysis (SMA, RSI, HHHL pattern)
4. Generate signals
5. Send alerts

**Key Change**: Only scans watchlist stocks (50), not full universe (500)

### 4.2 Prefect Detector Flow
**Objective**: Create on-demand/live detector workflow

**Tasks**:
1. Define Prefect tasks:
   - load_watchlist
   - fetch_market_data
   - detect_signals
   - send_alerts

2. Create detector flow
3. Support both on-demand and scheduled execution

**Tests**:
```python
async def test_detector_loads_watchlist()
async def test_detector_processes_signals()
async def test_detector_sends_alerts()
async def test_detector_handles_empty_watchlist()
```

## PHASE 5: CLI & Deployment (Week 6)

### 5.1 Enhanced CLI
**Objective**: Add commands for both workflows

**New Commands**:
```bash
orion screen --top-n 50              # Run screener manually
orion detect --strategy ofi           # Run detector
orion watchlist --show                # View current watchlist
orion watchlist --history             # View historical changes
```

### 5.2 Prefect Deployment
**Objective**: Deploy workflows to Prefect Cloud/self-hosted

**Tasks**:
1. Create deployment configurations
2. Set up Prefect Cloud account (free tier)
3. Deploy both workflows
4. Configure schedules:
   - Screener: Weekly (Sunday 8 PM)
   - Detector: Every 15 min during market hours (optional)

## PHASE 6: Testing & Optimization (Week 7)

### 6.1 Integration Testing
**Tasks**:
1. End-to-end screener workflow test
2. End-to-end detector workflow test
3. Test workflow failures and retries
4. Performance optimization

### 6.2 Monitoring & Observability
**Tasks**:
1. Configure Prefect logging
2. Add custom metrics tracking
3. Set up alert notifications for workflow failures
4. Create dashboard for monitoring

## Technology Stack Updates

### Additions:
- **Prefect**: Workflow orchestration (v2.x)
- **BeautifulSoup4/Selenium**: Web scraping for Finviz/Yahoo
- **aiosqlite**: Async SQLite for watchlist database

### Removals:
- ~~AWS Lambda~~
- ~~AWS EventBridge~~
- ~~AWS SES~~ (use SMTP directly)

### Updated Dependencies:
```toml
[tool.poetry.dependencies]
python = "^3.11"
prefect = "^2.14"           # Workflow orchestration
beautifulsoup4 = "^4.12"    # Web scraping
aiohttp = "^3.9"
pandas = "^2.1"
pydantic = "^2.5"
aiosqlite = "^0.19"         # Async SQLite
yfinance = "^0.2"
alpha-vantage = "^2.3"
pandas-ta = "^0.3"
click = "^8.1"
structlog = "^24.1"
```

## Migration Notes

### What Stays the Same:
- ✅ Technical indicator calculations (SMA, RSI)
- ✅ Pattern detection (HHHL)
- ✅ Option analysis (ATM puts, premium yield)
- ✅ Notification service (email alerts)
- ✅ Data provider abstraction
- ✅ Caching strategy
- ✅ Configuration management

### What Changes:
- ❌ No longer screening full S&P 500 weekly
- ✅ External screener provides initial candidates
- ✅ Ranking engine selects top 50
- ✅ Detector only monitors top 50 (faster, cheaper)
- ✅ Prefect handles scheduling and orchestration
- ✅ Watchlist database tracks curation history

## Performance Implications

### Before (Full Screening):
- 500 stocks screened
- ~1500 API calls
- 5-10 minutes runtime
- Higher API costs

### After (Screener + Detector):
- **Screener**: 200 candidates → 50 stocks, weekly
- **Detector**: 50 stocks, on-demand/live
- ~150 API calls per detector run
- 1-2 minutes runtime
- Lower API costs (10x reduction)

## Next Steps

1. **Review and Approve**: Get feedback on architectural changes
2. **Update Implementation Plan**: Incorporate changes into detailed plan
3. **Begin Phase 1**: Start with external screener integration
4. **Iterative Development**: Build and test incrementally
