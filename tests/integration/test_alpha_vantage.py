"""Integration tests for Alpha Vantage provider.

These tests make real API calls and require an Alpha Vantage API key.
Set ALPHA_VANTAGE_API_KEY environment variable to run these tests.

Note: Free tier has rate limits (5 calls/min, 500 calls/day).
These tests are marked with @pytest.mark.integration and can be skipped.
"""

import os
from datetime import date, timedelta

import pytest
from orion.config import DataProviderConfig
from orion.data.providers.alpha_vantage import AlphaVantageProvider


@pytest.fixture
def api_key() -> str:
    """Get Alpha Vantage API key from environment."""
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        pytest.skip("ALPHA_VANTAGE_API_KEY not set")
    return key


@pytest.fixture
def provider_config(api_key: str) -> DataProviderConfig:
    """Create provider configuration."""
    return DataProviderConfig(
        api_key=api_key,
        rate_limit=5,  # Free tier limit
    )


@pytest.fixture
def provider(provider_config: DataProviderConfig) -> AlphaVantageProvider:
    """Create Alpha Vantage provider."""
    return AlphaVantageProvider(provider_config)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_quote_real_data(provider: AlphaVantageProvider) -> None:
    """Fetch real quote from Alpha Vantage."""
    quote = await provider.get_quote("IBM")

    assert quote.symbol == "IBM"
    assert quote.price > 0
    assert quote.volume > 0
    assert quote.open > 0
    assert quote.high >= quote.low
    assert quote.previous_close is not None
    assert quote.change is not None

    # Validate calculated fields
    expected_change = quote.price - quote.previous_close
    assert abs(quote.change - expected_change) < 0.01


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_historical_prices_real_data(
    provider: AlphaVantageProvider,
) -> None:
    """Fetch real historical data from Alpha Vantage."""
    end = date.today()
    start = end - timedelta(days=30)

    data = await provider.get_historical_prices("IBM", start, end, interval="1d")

    assert len(data) > 0
    assert len(data) <= 30  # Should have at most 30 days of data

    # Verify chronological order
    for i in range(len(data) - 1):
        assert data[i].timestamp <= data[i + 1].timestamp

    # Verify data validity
    for ohlcv in data:
        assert ohlcv.open > 0
        assert ohlcv.high >= ohlcv.low
        assert ohlcv.high >= ohlcv.open
        assert ohlcv.high >= ohlcv.close
        assert ohlcv.low <= ohlcv.open
        assert ohlcv.low <= ohlcv.close
        assert ohlcv.volume >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_company_overview_real_data(
    provider: AlphaVantageProvider,
) -> None:
    """Fetch real company overview from Alpha Vantage."""
    overview = await provider.get_company_overview("IBM")

    assert overview.symbol == "IBM"
    assert overview.name is not None
    assert "IBM" in overview.name or "International Business" in overview.name
    assert overview.exchange is not None
    assert overview.sector is not None
    assert overview.industry is not None

    # Validate financial data
    assert overview.market_cap is not None
    assert overview.market_cap > 0

    # IBM is a large cap company
    assert overview.market_cap > 50_000_000_000  # > $50B

    # Check some expected fields are present
    if overview.revenue:
        assert overview.revenue > 0
    if overview.pe_ratio:
        assert overview.pe_ratio > 0
    if overview.eps:
        assert overview.eps != 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_company_overview_meets_criteria(
    provider: AlphaVantageProvider,
) -> None:
    """Verify company overview can be used for screening."""
    overview = await provider.get_company_overview("IBM")

    # IBM should meet reasonable screening criteria
    result = overview.meets_screener_criteria(
        min_revenue=10_000_000_000,  # $10B
        min_market_cap=50_000_000_000,  # $50B
    )

    assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_symbol_raises_error(
    provider: AlphaVantageProvider,
) -> None:
    """Invalid symbol raises appropriate error."""
    with pytest.raises((ValueError, RuntimeError)):
        await provider.get_quote("INVALID_SYMBOL_XYZ123")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limiting(provider: AlphaVantageProvider) -> None:
    """Verify rate limiting is working."""
    import time

    start = time.time()

    # Make 3 requests (should take at least 24 seconds with 5 req/min limit)
    await provider.get_quote("IBM")
    await provider.get_quote("AAPL")
    await provider.get_quote("MSFT")

    elapsed = time.time() - start

    # Should take at least 24 seconds (12 seconds between each call)
    # Allow some tolerance for processing time
    assert elapsed >= 20.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_option_chain_not_supported(
    provider: AlphaVantageProvider,
) -> None:
    """Alpha Vantage doesn't support option chains."""
    with pytest.raises(NotImplementedError):
        await provider.get_option_chain("IBM")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expirations_not_supported(
    provider: AlphaVantageProvider,
) -> None:
    """Alpha Vantage doesn't support option expirations."""
    with pytest.raises(NotImplementedError):
        await provider.get_available_expirations("IBM")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_multiple_symbols_sequential(
    provider: AlphaVantageProvider,
) -> None:
    """Fetch data for multiple symbols sequentially."""
    symbols = ["IBM", "AAPL", "MSFT"]

    for symbol in symbols:
        quote = await provider.get_quote(symbol)
        assert quote.symbol == symbol
        assert quote.price > 0

        overview = await provider.get_company_overview(symbol)
        assert overview.symbol == symbol
        assert overview.market_cap is not None
        assert overview.market_cap > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_historical_weekly_data(provider: AlphaVantageProvider) -> None:
    """Fetch weekly historical data."""
    end = date.today()
    start = end - timedelta(weeks=12)  # 12 weeks

    data = await provider.get_historical_prices("IBM", start, end, interval="1wk")

    assert len(data) > 0
    # Should have roughly 12 weeks of data
    assert 8 <= len(data) <= 15

    # Verify data validity
    for ohlcv in data:
        assert ohlcv.high >= ohlcv.low
        assert ohlcv.volume >= 0
