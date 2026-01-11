"""Tests for data providers."""

from datetime import date

import pytest
from orion.data.provider import MockDataProvider


class TestMockDataProvider:
    """Tests for MockDataProvider."""

    @pytest.fixture
    def provider(self) -> MockDataProvider:
        """Create mock provider instance."""
        return MockDataProvider()

    async def test_get_quote(self, provider: MockDataProvider) -> None:
        """Mock provider returns valid quote."""
        quote = await provider.get_quote("AAPL")

        assert quote.symbol == "AAPL"
        assert quote.price > 0
        assert quote.volume > 0
        assert quote.timestamp is not None
        assert quote.open > 0
        assert quote.high >= quote.low

    async def test_get_historical_prices(self, provider: MockDataProvider) -> None:
        """Mock provider returns historical data."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        data = await provider.get_historical_prices("AAPL", start, end)

        assert len(data) > 0
        # Check data is chronologically ordered
        for i in range(len(data) - 1):
            assert data[i].timestamp <= data[i + 1].timestamp

        # Check OHLCV data validity
        for ohlcv in data:
            assert ohlcv.high >= ohlcv.low
            assert ohlcv.high >= ohlcv.open
            assert ohlcv.high >= ohlcv.close
            assert ohlcv.volume >= 0

    async def test_get_option_chain(self, provider: MockDataProvider) -> None:
        """Mock provider returns valid option chain."""
        chain = await provider.get_option_chain("AAPL")

        assert chain.symbol == "AAPL"
        assert chain.underlying_price > 0
        assert chain.expiration is not None
        # Mock provider returns at least one put
        assert len(chain.puts) > 0

        # Validate put contract
        put = chain.puts[0]
        assert put.underlying_symbol == "AAPL"
        assert put.option_type == "put"
        assert put.strike > 0
        assert put.bid >= 0
        assert put.ask >= put.bid

    async def test_get_available_expirations(self, provider: MockDataProvider) -> None:
        """Mock provider returns expiration dates."""
        expirations = await provider.get_available_expirations("AAPL")

        assert len(expirations) > 0
        # Check dates are chronologically ordered
        for i in range(len(expirations) - 1):
            assert expirations[i] < expirations[i + 1]

    async def test_get_company_overview(self, provider: MockDataProvider) -> None:
        """Mock provider returns company overview."""
        overview = await provider.get_company_overview("AAPL")

        assert overview.symbol == "AAPL"
        assert overview.name is not None
        assert overview.exchange is not None
        assert overview.market_cap is not None
        assert overview.market_cap > 0

    async def test_multiple_symbols(self, provider: MockDataProvider) -> None:
        """Mock provider works with different symbols."""
        quote1 = await provider.get_quote("AAPL")
        quote2 = await provider.get_quote("MSFT")

        assert quote1.symbol == "AAPL"
        assert quote2.symbol == "MSFT"
