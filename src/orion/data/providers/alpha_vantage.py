"""Alpha Vantage data provider implementation."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import DataProviderConfig
from ...utils.logging import get_logger
from ..models import OHLCV, CompanyOverview, OptionChain, Quote
from ..provider import DataProvider

logger = get_logger(__name__)


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider.

    Provides comprehensive company fundamentals and financial data.
    Requires API key from https://www.alphavantage.co/
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, config: DataProviderConfig) -> None:
        """Initialize Alpha Vantage provider.

        Args:
            config: Data provider configuration with API key
        """
        if not config.api_key:
            raise ValueError("Alpha Vantage API key is required")

        self.api_key = config.api_key
        self.rate_limit_delay = 60.0 / config.rate_limit
        self._last_request_time = 0.0

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _make_request(self, function: str, symbol: str, **kwargs: Any) -> dict[str, Any]:
        """Make an API request to Alpha Vantage.

        Args:
            function: Alpha Vantage API function name
            symbol: Stock ticker symbol
            **kwargs: Additional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            RuntimeError: If API request fails or returns error
        """
        await self._rate_limit()

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
            **kwargs,
        }

        logger.debug(
            "alpha_vantage_request",
            function=function,
            symbol=symbol,
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    raise RuntimeError(f"Alpha Vantage API error: HTTP {response.status}")

                data = await response.json()

                # Check for API error messages
                if "Error Message" in data:
                    raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")

                if "Note" in data:
                    # API call frequency limit hit
                    logger.warning(
                        "alpha_vantage_rate_limit",
                        message=data["Note"],
                    )
                    raise RuntimeError("Alpha Vantage rate limit reached")

                result: dict[str, Any] = data
                return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote from Alpha Vantage."""
        data = await self._make_request("GLOBAL_QUOTE", symbol)

        if "Global Quote" not in data or not data["Global Quote"]:
            raise ValueError(f"No quote data found for symbol: {symbol}")

        quote_data = data["Global Quote"]

        quote = Quote(
            symbol=symbol,
            price=Decimal(quote_data["05. price"]),
            volume=int(quote_data["06. volume"]),
            timestamp=datetime.now(),  # Alpha Vantage doesn't provide exact timestamp
            open=Decimal(quote_data["02. open"]),
            high=Decimal(quote_data["03. high"]),
            low=Decimal(quote_data["04. low"]),
            close=Decimal(quote_data["05. price"]),
            previous_close=Decimal(quote_data["08. previous close"]),
            change=Decimal(quote_data["09. change"]),
            change_percent=float(quote_data["10. change percent"].rstrip("%")),
        )

        logger.info(
            "alpha_vantage_quote_fetched",
            symbol=symbol,
            price=float(quote.price),
        )

        return quote

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def get_historical_prices(
        self, symbol: str, start: date, end: date, interval: str = "1d"
    ) -> list[OHLCV]:
        """Get historical OHLCV data from Alpha Vantage.

        Note: Free tier limitations:
        - Only returns last 100 days of data (compact mode)
        - Full historical data requires premium subscription
        - For comprehensive historical data, use YahooFinanceProvider instead
        """
        # Map interval to Alpha Vantage function
        # Note: outputsize=full requires premium subscription, use compact for free tier
        if interval == "1d":
            function = "TIME_SERIES_DAILY"
            outputsize = "compact"  # Last 100 days only (free tier limitation)
        elif interval == "1wk":
            function = "TIME_SERIES_WEEKLY"
            outputsize = "compact"
        elif interval == "1mo":
            function = "TIME_SERIES_MONTHLY"
            outputsize = "compact"
        else:
            raise ValueError(f"Unsupported interval: {interval}")

        data = await self._make_request(function, symbol, outputsize=outputsize)

        # Find the time series key
        time_series_key = next((k for k in data.keys() if "Time Series" in k), None)

        if not time_series_key:
            raise ValueError(f"No time series data found for {symbol}")

        time_series = data[time_series_key]

        # Filter by date range and convert to OHLCV
        ohlcv_data = []
        for date_str, values in time_series.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            if start <= date_obj <= end:
                ohlcv = OHLCV(
                    timestamp=datetime.combine(date_obj, datetime.min.time()),
                    open=Decimal(values["1. open"]),
                    high=Decimal(values["2. high"]),
                    low=Decimal(values["3. low"]),
                    close=Decimal(values["4. close"]),
                    volume=int(values["5. volume"]),
                )
                ohlcv_data.append(ohlcv)

        # Sort chronologically
        ohlcv_data.sort(key=lambda x: x.timestamp)

        logger.info(
            "alpha_vantage_historical_fetched",
            symbol=symbol,
            count=len(ohlcv_data),
        )

        return ohlcv_data

    async def get_option_chain(self, symbol: str, expiration: date | None = None) -> OptionChain:
        """Get option chain.

        Note: Alpha Vantage does not provide option chain data.
        Use YahooFinanceProvider for options.
        """
        raise NotImplementedError(
            "Alpha Vantage does not support option chains. " "Use YahooFinanceProvider instead."
        )

    async def get_available_expirations(self, symbol: str) -> list[date]:
        """Get available option expirations.

        Note: Alpha Vantage does not provide option data.
        Use YahooFinanceProvider for options.
        """
        raise NotImplementedError(
            "Alpha Vantage does not support options. " "Use YahooFinanceProvider instead."
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def get_company_overview(self, symbol: str) -> CompanyOverview:
        """Get comprehensive company overview from Alpha Vantage."""
        data = await self._make_request("OVERVIEW", symbol)

        if not data or "Symbol" not in data:
            raise ValueError(f"No company data found for symbol: {symbol}")

        def to_decimal(value: str) -> Decimal | None:
            """Convert string to Decimal, return None if invalid."""
            try:
                return Decimal(value) if value and value != "None" else None
            except Exception:
                return None

        def to_int(value: str) -> int | None:
            """Convert string to int, return None if invalid."""
            try:
                return int(float(value)) if value and value != "None" else None
            except Exception:
                return None

        def to_float(value: str) -> float | None:
            """Convert string to float, return None if invalid."""
            try:
                return float(value) if value and value != "None" else None
            except Exception:
                return None

        overview = CompanyOverview(
            symbol=symbol,
            name=data.get("Name", symbol),
            exchange=data.get("Exchange", ""),
            sector=data.get("Sector"),
            industry=data.get("Industry"),
            market_cap=to_int(data.get("MarketCapitalization", "")),
            revenue=to_int(data.get("RevenueTTM", "")),
            revenue_per_share=to_decimal(data.get("RevenuePerShareTTM", "")),
            profit_margin=to_float(data.get("ProfitMargin", "")),
            operating_margin=to_float(data.get("OperatingMarginTTM", "")),
            pe_ratio=to_float(data.get("PERatio", "")),
            peg_ratio=to_float(data.get("PEGRatio", "")),
            book_value=to_decimal(data.get("BookValue", "")),
            dividend_per_share=to_decimal(data.get("DividendPerShare", "")),
            dividend_yield=to_float(data.get("DividendYield", "")),
            eps=to_decimal(data.get("EPS", "")),
            revenue_growth_yoy=to_float(data.get("QuarterlyRevenueGrowthYOY", "")),
            earnings_growth_yoy=to_float(data.get("QuarterlyEarningsGrowthYOY", "")),
            beta=to_float(data.get("Beta", "")),
            week_52_high=to_decimal(data.get("52WeekHigh", "")),
            week_52_low=to_decimal(data.get("52WeekLow", "")),
            moving_average_50=to_decimal(data.get("50DayMovingAverage", "")),
            moving_average_200=to_decimal(data.get("200DayMovingAverage", "")),
            shares_outstanding=to_int(data.get("SharesOutstanding", "")),
        )

        logger.info(
            "alpha_vantage_overview_fetched",
            symbol=symbol,
            name=overview.name,
            sector=overview.sector,
            revenue=overview.revenue,
        )

        return overview
