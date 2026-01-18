"""Stock screener for automated screening and signal detection.

This module provides the StockScreener class that orchestrates the end-to-end
screening pipeline: fetching data, analyzing indicators, evaluating strategies,
and finding options for trading opportunities.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime

from orion.analysis.indicators import IndicatorCalculator
from orion.data.models import Quote, TechnicalIndicators
from orion.data.provider import DataProvider
from orion.strategies.evaluator import RuleEvaluator
from orion.strategies.models import OptionRecommendation, Strategy
from orion.strategies.option_analyzer import OptionAnalyzer
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="StockScreener")


@dataclass
class ScreeningResult:
    """Result of screening a single symbol.

    Attributes:
        symbol: The stock symbol that was screened
        timestamp: When the screening was performed
        matches: Whether the symbol matched the strategy criteria
        signal_strength: Calculated signal strength (0.0 to 1.0)
        conditions_met: List of condition types that were met
        conditions_missed: List of condition types that were not met
        quote: Current quote data for the symbol
        indicators: Calculated technical indicators
        option_recommendation: Recommended option contract (if applicable)
        evaluation_details: Additional evaluation details
        error: Error message if screening failed
    """

    symbol: str
    timestamp: datetime
    matches: bool
    signal_strength: float
    conditions_met: list[str]
    conditions_missed: list[str]
    quote: Quote | None
    indicators: TechnicalIndicators | None
    option_recommendation: OptionRecommendation | None
    evaluation_details: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class ScreeningStats:
    """Statistics from a screening run.

    Attributes:
        total_symbols: Total number of symbols processed
        successful: Number of successfully screened symbols
        failed: Number of symbols that failed to screen
        matches: Number of symbols that matched the strategy
        start_time: When the screening run started
        end_time: When the screening run ended
        duration_seconds: Total duration of the screening run
    """

    total_symbols: int
    successful: int
    failed: int
    matches: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_symbols == 0:
            return 0.0
        return (self.successful / self.total_symbols) * 100


class StockScreener:
    """Orchestrate the end-to-end stock screening pipeline.

    The screener processes symbols through the full analysis pipeline:
    1. Fetch quote for symbol
    2. Fetch historical prices (1 year)
    3. Calculate technical indicators
    4. Evaluate strategy conditions
    5. If match: fetch option chain, find best ATM put
    6. Return ScreeningResult

    Example:
        >>> screener = StockScreener(provider, strategy, max_concurrent=5)
        >>> result = await screener.screen_symbol("AAPL")
        >>> print(result.matches, result.signal_strength)
        >>>
        >>> async for result in screener.screen_batch(["AAPL", "MSFT", "GOOGL"]):
        ...     if result.matches:
        ...         print(f"Match: {result.symbol}")
    """

    def __init__(
        self,
        provider: DataProvider,
        strategy: Strategy,
        max_concurrent: int = 5,
        historical_days: int = 252,
    ) -> None:
        """Initialize the StockScreener.

        Args:
            provider: Data provider for fetching market data
            strategy: Trading strategy to evaluate against
            max_concurrent: Maximum number of concurrent screenings
            historical_days: Number of days of historical data to fetch (default 252 = 1 year)
        """
        self.provider = provider
        self.strategy = strategy
        self.max_concurrent = max_concurrent
        self.historical_days = historical_days

        self.indicator_calc = IndicatorCalculator()
        self.option_analyzer = OptionAnalyzer()
        self._evaluator = RuleEvaluator(strategy)
        self._logger = logger
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def screen_symbol(self, symbol: str) -> ScreeningResult:
        """Screen a single symbol through the full pipeline.

        Args:
            symbol: Stock symbol to screen

        Returns:
            ScreeningResult with match status and recommendation
        """
        async with self._semaphore:
            start_time = datetime.now()
            self._logger.info("screening_start", symbol=symbol, strategy=self.strategy.name)

            try:
                # Step 1: Fetch quote
                quote = await self.provider.get_quote(symbol)
                if quote is None:
                    return ScreeningResult(
                        symbol=symbol,
                        timestamp=start_time,
                        matches=False,
                        signal_strength=0.0,
                        conditions_met=[],
                        conditions_missed=[c.type for c in self.strategy.entry_conditions],
                        quote=None,
                        indicators=None,
                        option_recommendation=None,
                        error="Failed to fetch quote",
                    )

                # Step 2: Fetch historical prices
                end_date = date.today()
                start_date = date.fromordinal(end_date.toordinal() - self.historical_days)
                historical = await self.provider.get_historical_prices(
                    symbol, start=start_date, end=end_date, interval="1d"
                )

                if not historical or len(historical) < 60:
                    self._logger.warning(
                        "insufficient_historical_data",
                        symbol=symbol,
                        data_points=len(historical) if historical else 0,
                    )
                    return ScreeningResult(
                        symbol=symbol,
                        timestamp=start_time,
                        matches=False,
                        signal_strength=0.0,
                        conditions_met=[],
                        conditions_missed=[c.type for c in self.strategy.entry_conditions],
                        quote=quote,
                        indicators=None,
                        option_recommendation=None,
                        error=f"Insufficient historical data: {len(historical) if historical else 0} points",
                    )

                # Step 3: Calculate technical indicators
                indicators = self.indicator_calc.calculate(historical, symbol)

                # Step 4: Evaluate strategy conditions
                evaluation = await self._evaluator.evaluate(symbol, quote, historical, indicators)

                # Step 5: If match, fetch options and find best opportunity
                option_recommendation: OptionRecommendation | None = None
                if evaluation.matches:
                    self._logger.info("strategy_match_found", symbol=symbol)
                    try:
                        # Get available expirations
                        expirations = await self.provider.get_available_expirations(symbol)

                        if expirations:
                            # Filter by target DTE range
                            target_expirations = [
                                exp
                                for exp in expirations
                                if self.strategy.option_screening.min_dte
                                <= (exp - date.today()).days
                                <= self.strategy.option_screening.max_dte
                            ]

                            if target_expirations:
                                # Get option chains for target expirations
                                option_chains = []
                                for exp in target_expirations[:3]:  # Limit to 3 expirations
                                    try:
                                        chain = await self.provider.get_option_chain(symbol, exp)
                                        if chain:
                                            option_chains.append(chain)
                                    except Exception as e:
                                        self._logger.warning(
                                            "option_chain_fetch_failed",
                                            symbol=symbol,
                                            expiration=exp,
                                            error=str(e),
                                        )
                                        continue

                                if option_chains:
                                    option_recommendation = (
                                        self.option_analyzer.analyze_all_expirations(
                                            option_chains,
                                            self.strategy.option_screening,
                                            date.today(),
                                        )
                                    )
                                    if option_recommendation:
                                        self._logger.info(
                                            "option_recommendation_found",
                                            symbol=symbol,
                                            option=option_recommendation.symbol,
                                            yield_val=option_recommendation.premium_yield,
                                        )

                    except Exception as e:
                        self._logger.error(
                            "option_analysis_failed",
                            symbol=symbol,
                            error=str(e),
                        )

                duration = (datetime.now() - start_time).total_seconds()

                self._logger.info(
                    "screening_complete",
                    symbol=symbol,
                    matches=evaluation.matches,
                    signal_strength=evaluation.signal_strength,
                    conditions_met=len(evaluation.conditions_met),
                    duration_seconds=duration,
                )

                return ScreeningResult(
                    symbol=symbol,
                    timestamp=start_time,
                    matches=evaluation.matches,
                    signal_strength=evaluation.signal_strength,
                    conditions_met=evaluation.conditions_met,
                    conditions_missed=evaluation.conditions_missed,
                    quote=quote,
                    indicators=indicators,
                    option_recommendation=option_recommendation,
                    evaluation_details=evaluation.details or {},
                )

            except Exception as e:
                self._logger.error(
                    "screening_error",
                    symbol=symbol,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return ScreeningResult(
                    symbol=symbol,
                    timestamp=start_time,
                    matches=False,
                    signal_strength=0.0,
                    conditions_met=[],
                    conditions_missed=[c.type for c in self.strategy.entry_conditions],
                    quote=None,
                    indicators=None,
                    option_recommendation=None,
                    error=f"Screening error: {str(e)}",
                )

    async def screen_batch(self, symbols: list[str]) -> asyncio.Queue[ScreeningResult]:
        """Screen multiple symbols concurrently.

        Processes symbols in batches with controlled concurrency to respect
        API rate limits and resource constraints.

        Args:
            symbols: List of stock symbols to screen

        Yields:
            ScreeningResult for each symbol as it completes
        """
        results: asyncio.Queue[ScreeningResult] = asyncio.Queue()

        async def screen_and_queue(symbol: str) -> None:
            """Screen a symbol and put result in queue."""
            result = await self.screen_symbol(symbol)
            await results.put(result)

        # Create tasks for all symbols
        tasks = [screen_and_queue(symbol) for symbol in symbols]

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def screen_batch_iter(self, symbols: list[str]) -> list[ScreeningResult]:
        """Screen multiple symbols and return results as a list.

        Args:
            symbols: List of stock symbols to screen

        Returns:
            List of ScreeningResult objects
        """
        results_queue = await self.screen_batch(symbols)
        results = []
        while not results_queue.empty():
            try:
                result = results_queue.get_nowait()
                results.append(result)
            except asyncio.QueueEmpty:
                break
        return results

    async def screen_and_filter(
        self, symbols: list[str]
    ) -> tuple[list[ScreeningResult], ScreeningStats]:
        """Screen multiple symbols and return only matches with statistics.

        Args:
            symbols: List of stock symbols to screen

        Returns:
            Tuple of (matching results, screening statistics)
        """
        start_time = datetime.now()

        all_results = await self.screen_batch_iter(symbols)

        matches = [r for r in all_results if r.matches]
        failed = [r for r in all_results if r.error is not None]
        successful = [r for r in all_results if r.error is None]

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        stats = ScreeningStats(
            total_symbols=len(symbols),
            successful=len(successful),
            failed=len(failed),
            matches=len(matches),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
        )

        self._logger.info(
            "batch_screening_complete",
            strategy=self.strategy.name,
            total_symbols=stats.total_symbols,
            successful=stats.successful,
            failed=stats.failed,
            matches=stats.matches,
            duration_seconds=stats.duration_seconds,
        )

        return matches, stats
