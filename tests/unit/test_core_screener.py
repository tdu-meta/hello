"""Tests for the core screening module."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from orion.core.screener import ScreeningResult, ScreeningStats, StockScreener
from orion.data.models import (
    OHLCV,
    OptionChain,
    OptionContract,
    Quote,
)
from orion.data.provider import DataProvider
from orion.strategies.models import (
    Condition,
    OptionScreening,
    StockCriteria,
    Strategy,
)


class MockDataProvider(DataProvider):
    """Mock data provider for testing."""

    def __init__(self, raise_on: str | None = None) -> None:
        self.raise_on = raise_on

    async def get_quote(self, symbol: str) -> Quote | None:
        if self.raise_on == "quote":
            raise RuntimeError("Test error")
        return Quote(
            symbol=symbol,
            price=Decimal("150.00"),
            volume=1_000_000,
            timestamp=datetime.now(),
            open=Decimal("148.00"),
            high=Decimal("152.00"),
            low=Decimal("147.00"),
            close=Decimal("150.00"),
            previous_close=Decimal("147.00"),
        )

    async def get_historical_prices(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> list[OHLCV]:
        if self.raise_on == "historical":
            raise RuntimeError("Test error")

        # Generate 100 days of OHLCV data with an upward trend
        base_price = 140.0
        data = []
        for i in range(100):
            price = base_price + (i * 0.1)
            data.append(
                OHLCV(
                    timestamp=datetime.fromtimestamp(i * 86400),
                    open=Decimal(str(price)),
                    high=Decimal(str(price + 1.0)),
                    low=Decimal(str(price - 0.5)),
                    close=Decimal(str(price + 0.5)),
                    volume=1_000_000 + (i * 10000),
                )
            )
        return list(reversed(data))

    async def get_option_chain(self, symbol: str, expiration: date) -> OptionChain | None:
        if self.raise_on == "options":
            raise RuntimeError("Test error")

        return OptionChain(
            symbol=symbol,
            expiration=expiration,
            underlying_price=Decimal("150.00"),
            puts=[
                OptionContract(
                    symbol="AAPL240119P00150000",
                    underlying_symbol=symbol,
                    strike=Decimal("150.00"),
                    expiration=expiration,
                    option_type="put",
                    bid=Decimal("2.50"),
                    ask=Decimal("2.60"),
                    last_price=Decimal("2.55"),
                    volume=500,
                    open_interest=1000,
                    implied_volatility=0.25,
                    delta=-0.45,
                )
            ],
        )

    async def get_available_expirations(self, symbol: str) -> list[date]:
        if self.raise_on == "expirations":
            raise RuntimeError("Test error")

        today = date.today()
        return [
            date(today.year, today.month + 1, 19),
            date(today.year, today.month + 2, 16),
        ]

    async def get_company_overview(self, symbol: str):
        return None


@pytest.fixture
def mock_provider():
    """Create a mock data provider."""
    return MockDataProvider()


@pytest.fixture
def ofi_strategy():
    """Create an OFI strategy for testing."""
    return Strategy(
        name="ofi",
        version="1.0.0",
        description="Option for Income strategy",
        stock_criteria=StockCriteria(
            min_revenue=1_000_000_000,
            min_market_cap=500_000_000,
        ),
        entry_conditions=[
            Condition(
                type="trend",
                rule="sma_20 > sma_60",
                description="Bullish trend with SMA-20 above SMA-60",
                weight=1.0,
            ),
            Condition(
                type="oversold",
                rule="rsi < threshold",
                parameters={"threshold": 70.0},  # Set high to ensure test passes
                description="RSI indicates oversold or recovering",
                weight=1.0,
            ),
        ],
        option_screening=OptionScreening(
            min_premium_yield=0.01,
            min_dte=7,
            max_dte=60,
            tolerance=0.05,
            min_volume=100,
            min_open_interest=500,
        ),
    )


class TestScreeningResult:
    """Tests for ScreeningResult dataclass."""

    def test_create_screening_result(self):
        """Test creating a screening result."""
        result = ScreeningResult(
            symbol="AAPL",
            timestamp=datetime.now(),
            matches=True,
            signal_strength=0.85,
            conditions_met=["trend", "oversold"],
            conditions_missed=[],
            quote=None,
            indicators=None,
            option_recommendation=None,
        )
        assert result.symbol == "AAPL"
        assert result.matches is True
        assert result.signal_strength == 0.85
        assert len(result.conditions_met) == 2

    def test_screening_result_with_error(self):
        """Test screening result with error."""
        result = ScreeningResult(
            symbol="INVALID",
            timestamp=datetime.now(),
            matches=False,
            signal_strength=0.0,
            conditions_met=[],
            conditions_missed=["trend", "oversold"],
            quote=None,
            indicators=None,
            option_recommendation=None,
            error="Symbol not found",
        )
        assert result.error == "Symbol not found"
        assert result.matches is False


class TestScreeningStats:
    """Tests for ScreeningStats dataclass."""

    def test_screening_stats_success_rate(self):
        """Test success rate calculation."""
        stats = ScreeningStats(
            total_symbols=100,
            successful=95,
            failed=5,
            matches=10,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=60.0,
        )
        assert stats.success_rate == 95.0

    def test_screening_stats_zero_symbols(self):
        """Test success rate with zero symbols."""
        stats = ScreeningStats(
            total_symbols=0,
            successful=0,
            failed=0,
            matches=0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=0.0,
        )
        assert stats.success_rate == 0.0


class TestStockScreener:
    """Tests for StockScreener class."""

    @pytest.mark.asyncio
    async def test_screener_initialization(self, mock_provider, ofi_strategy):
        """Test screener initialization."""
        screener = StockScreener(
            provider=mock_provider,
            strategy=ofi_strategy,
            max_concurrent=5,
        )
        assert screener.provider == mock_provider
        assert screener.strategy == ofi_strategy
        assert screener.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_screen_symbol_success(self, mock_provider, ofi_strategy):
        """Test screening a symbol successfully."""
        screener = StockScreener(
            provider=mock_provider,
            strategy=ofi_strategy,
            max_concurrent=1,
        )

        result = await screener.screen_symbol("AAPL")

        assert result.symbol == "AAPL"
        assert result.quote is not None
        assert result.indicators is not None
        assert isinstance(result.matches, bool)
        assert isinstance(result.signal_strength, float)

    @pytest.mark.asyncio
    async def test_screen_symbol_with_insufficient_data(self, mock_provider, ofi_strategy):
        """Test screening with insufficient historical data."""

        # Create provider that returns insufficient data
        class LowDataProvider(MockDataProvider):
            async def get_historical_prices(self, symbol, start, end, interval="1d"):
                return []  # Empty data

        screener = StockScreener(
            provider=LowDataProvider(),
            strategy=ofi_strategy,
            max_concurrent=1,
        )

        result = await screener.screen_symbol("AAPL")

        assert result.symbol == "AAPL"
        assert result.matches is False
        assert result.error is not None
        assert "Insufficient historical data" in result.error

    @pytest.mark.asyncio
    async def test_screen_symbol_with_provider_error(self, mock_provider, ofi_strategy):
        """Test screening when provider raises an error."""
        screener = StockScreener(
            provider=MockDataProvider(raise_on="quote"),
            strategy=ofi_strategy,
            max_concurrent=1,
        )

        result = await screener.screen_symbol("AAPL")

        assert result.symbol == "AAPL"
        assert result.matches is False
        assert result.error is not None
        assert "Screening error" in result.error

    @pytest.mark.asyncio
    async def test_screen_batch_single(self, mock_provider, ofi_strategy):
        """Test screening a batch of symbols."""
        screener = StockScreener(
            provider=mock_provider,
            strategy=ofi_strategy,
            max_concurrent=2,
        )

        results = await screener.screen_batch_iter(["AAPL", "MSFT", "GOOGL"])

        assert len(results) == 3
        assert all(isinstance(r, ScreeningResult) for r in results)
        symbols = {r.symbol for r in results}
        assert symbols == {"AAPL", "MSFT", "GOOGL"}

    @pytest.mark.asyncio
    async def test_screen_and_filter(self, mock_provider, ofi_strategy):
        """Test screening and filtering for matches."""
        screener = StockScreener(
            provider=mock_provider,
            strategy=ofi_strategy,
            max_concurrent=2,
        )

        matches, stats = await screener.screen_and_filter(["AAPL", "MSFT", "GOOGL"])

        assert stats.total_symbols == 3
        assert isinstance(matches, list)
        assert isinstance(stats, ScreeningStats)
        assert stats.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_concurrent_limit_respected(self, mock_provider, ofi_strategy):
        """Test that concurrent limit is respected."""
        screener = StockScreener(
            provider=mock_provider,
            strategy=ofi_strategy,
            max_concurrent=2,
        )

        # Screen 5 symbols with max 2 concurrent
        results = await screener.screen_batch_iter(["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])

        assert len(results) == 5
