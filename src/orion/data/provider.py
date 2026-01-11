"""Abstract data provider interface for market data."""

from abc import ABC, abstractmethod
from datetime import date, datetime

from .models import OHLCV, CompanyOverview, OptionChain, Quote


class DataProvider(ABC):
    """Abstract base class for data providers.

    All data providers must implement these methods to provide
    market data from various sources (Alpha Vantage, Yahoo Finance, etc).
    """

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Quote with current price, volume, and OHLC data

        Raises:
            ValueError: If symbol is invalid or not found
            RuntimeError: If API request fails
        """
        pass

    @abstractmethod
    async def get_historical_prices(
        self, symbol: str, start: date, end: date, interval: str = "1d"
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock ticker symbol
            start: Start date for historical data
            end: End date for historical data
            interval: Data interval ('1d', '1wk', '1mo')

        Returns:
            List of OHLCV data points in chronological order

        Raises:
            ValueError: If symbol or date range is invalid
            RuntimeError: If API request fails
        """
        pass

    @abstractmethod
    async def get_option_chain(self, symbol: str, expiration: date | None = None) -> OptionChain:
        """Get option chain for a symbol.

        Args:
            symbol: Stock ticker symbol
            expiration: Specific expiration date (if None, gets nearest expiration)

        Returns:
            OptionChain with calls and puts for the expiration

        Raises:
            ValueError: If symbol is invalid or options not available
            RuntimeError: If API request fails
        """
        pass

    @abstractmethod
    async def get_available_expirations(self, symbol: str) -> list[date]:
        """Get available option expiration dates for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            List of available expiration dates in chronological order

        Raises:
            ValueError: If symbol is invalid or options not available
            RuntimeError: If API request fails
        """
        pass

    @abstractmethod
    async def get_company_overview(self, symbol: str) -> CompanyOverview:
        """Get company fundamental information.

        Args:
            symbol: Stock ticker symbol

        Returns:
            CompanyOverview with fundamentals and financials

        Raises:
            ValueError: If symbol is invalid or not found
            RuntimeError: If API request fails
        """
        pass


class MockDataProvider(DataProvider):
    """Mock data provider for testing.

    Returns fake but realistic data for all methods.
    Useful for unit tests and development without API keys.
    """

    def __init__(self) -> None:
        """Initialize mock provider with sample data."""
        from decimal import Decimal

        self._mock_price = Decimal("150.00")

    async def get_quote(self, symbol: str) -> Quote:
        """Return a mock quote."""
        from decimal import Decimal

        return Quote(
            symbol=symbol,
            price=self._mock_price,
            volume=1000000,
            timestamp=datetime.now(),
            open=Decimal("148.00"),
            high=Decimal("151.00"),
            low=Decimal("147.50"),
            close=self._mock_price,
            previous_close=Decimal("149.00"),
        )

    async def get_historical_prices(
        self, symbol: str, start: date, end: date, interval: str = "1d"
    ) -> list[OHLCV]:
        """Return mock historical data."""
        from decimal import Decimal

        # Generate simple mock data for 5 days
        data = []
        base_price = Decimal("150.00")
        for i in range(5):
            price = base_price + Decimal(i)
            data.append(
                OHLCV(
                    timestamp=datetime.combine(start, datetime.min.time()),
                    open=price - Decimal("1"),
                    high=price + Decimal("2"),
                    low=price - Decimal("2"),
                    close=price,
                    volume=1000000 + i * 10000,
                )
            )
        return data

    async def get_option_chain(self, symbol: str, expiration: date | None = None) -> OptionChain:
        """Return mock option chain."""
        from decimal import Decimal

        from .models import OptionContract

        if expiration is None:
            expiration = date.today()

        # Create mock ATM put
        put = OptionContract(
            symbol=f"{symbol}240119P00150000",
            underlying_symbol=symbol,
            strike=Decimal("150.00"),
            expiration=expiration,
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            delta=-0.50,
        )

        return OptionChain(
            symbol=symbol,
            expiration=expiration,
            underlying_price=self._mock_price,
            puts=[put],
            calls=[],
        )

    async def get_available_expirations(self, symbol: str) -> list[date]:
        """Return mock expiration dates."""
        from datetime import timedelta

        today = date.today()
        return [
            today + timedelta(days=7),
            today + timedelta(days=14),
            today + timedelta(days=30),
        ]

    async def get_company_overview(self, symbol: str) -> CompanyOverview:
        """Return mock company overview."""
        from decimal import Decimal

        return CompanyOverview(
            symbol=symbol,
            name=f"{symbol} Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            market_cap=1_000_000_000_000,  # $1T
            revenue=100_000_000_000,  # $100B
            pe_ratio=25.0,
            eps=Decimal("6.00"),
            beta=1.2,
        )
