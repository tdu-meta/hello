"""Yahoo Finance data provider implementation."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from ...utils.logging import get_logger
from ..models import OHLCV, CompanyOverview, OptionChain, OptionContract, Quote
from ..provider import DataProvider

logger = get_logger(__name__)


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider.

    Uses yfinance library to fetch real-time quotes, historical data,
    and option chains. No API key required but has rate limits.
    """

    def __init__(self, rate_limit_delay: float = 0.5) -> None:
        """Initialize Yahoo Finance provider.

        Args:
            rate_limit_delay: Delay between requests in seconds (default 0.5)
        """
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote from Yahoo Finance."""
        await self._rate_limit()

        logger.debug("fetching_quote", symbol=symbol)

        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
        hist = await loop.run_in_executor(None, lambda: ticker.history(period="5d"))

        if hist.empty:
            raise ValueError(f"No data found for symbol: {symbol}")

        latest = hist.iloc[-1]
        timestamp = hist.index[-1].to_pydatetime()

        # Get previous close from second-to-last day if available
        previous_close = None
        if len(hist) > 1:
            previous_close = Decimal(str(hist.iloc[-2]["Close"]))

        quote = Quote(
            symbol=symbol,
            price=Decimal(str(latest["Close"])),
            volume=int(latest["Volume"]),
            timestamp=timestamp,
            open=Decimal(str(latest["Open"])),
            high=Decimal(str(latest["High"])),
            low=Decimal(str(latest["Low"])),
            close=Decimal(str(latest["Close"])),
            previous_close=previous_close,
        )

        logger.info(
            "quote_fetched",
            symbol=symbol,
            price=float(quote.price),
            volume=quote.volume,
        )

        return quote

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_historical_prices(
        self, symbol: str, start: date, end: date, interval: str = "1d"
    ) -> list[OHLCV]:
        """Get historical OHLCV data from Yahoo Finance."""
        await self._rate_limit()

        logger.debug(
            "fetching_historical_data",
            symbol=symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            interval=interval,
        )

        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
        hist = await loop.run_in_executor(
            None,
            lambda: ticker.history(start=start, end=end, interval=interval, auto_adjust=False),
        )

        if hist.empty:
            raise ValueError(f"No historical data found for {symbol} from {start} to {end}")

        # Convert DataFrame to OHLCV objects
        data = []
        for idx, row in hist.iterrows():
            ohlcv = OHLCV(
                timestamp=idx.to_pydatetime(),
                open=Decimal(str(row["Open"])),
                high=Decimal(str(row["High"])),
                low=Decimal(str(row["Low"])),
                close=Decimal(str(row["Close"])),
                volume=int(row["Volume"]),
                adjusted_close=Decimal(str(row["Adj Close"])),
            )
            data.append(ohlcv)

        logger.info(
            "historical_data_fetched",
            symbol=symbol,
            count=len(data),
            start=start.isoformat(),
            end=end.isoformat(),
        )

        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_option_chain(self, symbol: str, expiration: date | None = None) -> OptionChain:
        """Get option chain from Yahoo Finance."""
        await self._rate_limit()

        logger.debug(
            "fetching_option_chain",
            symbol=symbol,
            expiration=expiration.isoformat() if expiration else None,
        )

        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)

        # Get available expirations
        expirations = await loop.run_in_executor(None, lambda: ticker.options)

        if not expirations:
            raise ValueError(f"No options available for symbol: {symbol}")

        # If no specific expiration provided, use the first one
        if expiration is None:
            expiration_str = expirations[0]
        else:
            expiration_str = expiration.isoformat()
            if expiration_str not in expirations:
                raise ValueError(f"Expiration {expiration_str} not available for {symbol}")

        # Get option chain for expiration
        opt = await loop.run_in_executor(None, ticker.option_chain, expiration_str)

        # Get current price
        info = await loop.run_in_executor(None, lambda: ticker.info)
        current_price = Decimal(str(info.get("currentPrice", 0)))

        # Parse calls
        calls = []
        if not opt.calls.empty:
            for _, row in opt.calls.iterrows():
                calls.append(self._parse_option_contract(row, symbol, "call"))

        # Parse puts
        puts = []
        if not opt.puts.empty:
            for _, row in opt.puts.iterrows():
                puts.append(self._parse_option_contract(row, symbol, "put"))

        chain = OptionChain(
            symbol=symbol,
            expiration=datetime.strptime(expiration_str, "%Y-%m-%d").date(),
            underlying_price=current_price,
            calls=calls,
            puts=puts,
        )

        logger.info(
            "option_chain_fetched",
            symbol=symbol,
            expiration=expiration_str,
            calls_count=len(calls),
            puts_count=len(puts),
        )

        return chain

    def _parse_option_contract(
        self, row: Any, underlying_symbol: str, option_type: str
    ) -> OptionContract:
        """Parse option contract from DataFrame row."""
        return OptionContract(
            symbol=row["contractSymbol"],
            underlying_symbol=underlying_symbol,
            strike=Decimal(str(row["strike"])),
            expiration=datetime.fromtimestamp(row["lastTradeDate"]).date(),
            option_type=option_type,  # type: ignore
            bid=Decimal(str(row.get("bid", 0))),
            ask=Decimal(str(row.get("ask", 0))),
            last_price=Decimal(str(row.get("lastPrice", 0))),
            volume=int(row.get("volume", 0) or 0),
            open_interest=int(row.get("openInterest", 0) or 0),
            implied_volatility=float(row.get("impliedVolatility", 0) or 0),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_available_expirations(self, symbol: str) -> list[date]:
        """Get available option expiration dates."""
        await self._rate_limit()

        logger.debug("fetching_expirations", symbol=symbol)

        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
        expirations = await loop.run_in_executor(None, lambda: ticker.options)

        if not expirations:
            raise ValueError(f"No options available for symbol: {symbol}")

        # Convert string dates to date objects
        expiration_dates = [datetime.strptime(exp, "%Y-%m-%d").date() for exp in expirations]

        logger.info(
            "expirations_fetched",
            symbol=symbol,
            count=len(expiration_dates),
        )

        return expiration_dates

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_company_overview(self, symbol: str) -> CompanyOverview:
        """Get company overview from Yahoo Finance.

        Note: Yahoo Finance provides limited fundamental data compared to
        Alpha Vantage. For comprehensive fundamentals, use AlphaVantageProvider.
        """
        await self._rate_limit()

        logger.debug("fetching_company_overview", symbol=symbol)

        # Run blocking yfinance call in executor
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
        info = await loop.run_in_executor(None, lambda: ticker.info)

        if not info:
            raise ValueError(f"No company data found for symbol: {symbol}")

        overview = CompanyOverview(
            symbol=symbol,
            name=info.get("longName", symbol),
            exchange=info.get("exchange", ""),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            revenue=info.get("totalRevenue"),
            pe_ratio=info.get("trailingPE"),
            eps=Decimal(str(info["trailingEps"])) if "trailingEps" in info else None,
            beta=info.get("beta"),
            dividend_yield=info.get("dividendYield"),
            week_52_high=Decimal(str(info["fiftyTwoWeekHigh"]))
            if "fiftyTwoWeekHigh" in info
            else None,
            week_52_low=Decimal(str(info["fiftyTwoWeekLow"]))
            if "fiftyTwoWeekLow" in info
            else None,
            moving_average_50=Decimal(str(info["fiftyDayAverage"]))
            if "fiftyDayAverage" in info
            else None,
            moving_average_200=Decimal(str(info["twoHundredDayAverage"]))
            if "twoHundredDayAverage" in info
            else None,
            shares_outstanding=info.get("sharesOutstanding"),
        )

        logger.info(
            "company_overview_fetched",
            symbol=symbol,
            name=overview.name,
            sector=overview.sector,
        )

        return overview
