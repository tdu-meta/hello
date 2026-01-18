"""Option analyzer for finding and analyzing ATM put options.

This module provides the OptionAnalyzer class for identifying at-the-money
put options, calculating yields, and finding the best opportunities for
the Option for Income strategy.
"""

from datetime import date

from orion.data.models import OptionChain, OptionContract
from orion.strategies.models import OptionRecommendation, OptionScreening
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="OptionAnalyzer")


class OptionAnalyzer:
    """Analyze option contracts for OFI strategy opportunities.

    The analyzer finds at-the-money put options, calculates annualized
    premium yields, filters by liquidity, and identifies the best
    opportunities.

    Example:
        >>> analyzer = OptionAnalyzer()
        >>> rec = analyzer.find_best_opportunity(chain, screening)
        >>> print(rec.symbol, rec.premium_yield)
    """

    def __init__(self) -> None:
        """Initialize the OptionAnalyzer."""
        self._logger = logger

    def find_atm_puts(
        self,
        option_chain: OptionChain,
        tolerance: float = 0.05,
    ) -> list[OptionContract]:
        """Find at-the-money put options within tolerance.

        Args:
            option_chain: Option chain to search
            tolerance: Tolerance as percentage of underlying price
                      (e.g., 0.05 = 5% above/below current price)

        Returns:
            List of put options sorted by proximity to ATM (closest first)

        Raises:
            ValueError: If option_chain has no underlying price
        """
        underlying = float(option_chain.underlying_price)
        if underlying <= 0:
            raise ValueError(f"Invalid underlying price: {underlying}")

        lower_bound = underlying * (1 - tolerance)
        upper_bound = underlying * (1 + tolerance)

        # Filter puts within tolerance range
        atm_puts = [
            put for put in option_chain.puts if lower_bound <= float(put.strike) <= upper_bound
        ]

        # Sort by proximity to underlying price (ATM first)
        atm_puts.sort(key=lambda p: abs(float(p.strike) - underlying))

        self._logger.debug(
            "found_atm_puts",
            symbol=option_chain.symbol,
            underlying=underlying,
            tolerance=tolerance,
            count=len(atm_puts),
        )

        return atm_puts

    def calculate_premium_yield(
        self,
        put: OptionContract,
        stock_price: float,
        expiration: date,
        current_date: date | None = None,
    ) -> float:
        """Calculate annualized premium yield for a put option.

        The annualized yield is calculated as:
        (premium / stock_price) * (365 / days_to_expiration)

        Args:
            put: The put option contract
            stock_price: Current stock price
            expiration: Option expiration date
            current_date: Current date (defaults to today)

        Returns:
            Annualized yield as a decimal (e.g., 0.15 for 15%)

        Raises:
            ValueError: If days to expiration is zero or negative
        """
        if current_date is None:
            current_date = date.today()

        days_to_exp = (expiration - current_date).days

        if days_to_exp <= 0:
            raise ValueError(f"Invalid days to expiration: {days_to_exp}")

        # Use mid price as premium
        premium = float(put.mid_price)

        # Calculate yield
        yield_per_day = premium / stock_price
        annualized_yield = yield_per_day * (365 / days_to_exp)

        self._logger.debug(
            "calculated_premium_yield",
            symbol=put.symbol,
            strike=put.strike,
            premium=premium,
            days_to_exp=days_to_exp,
            annualized_yield=annualized_yield,
        )

        return annualized_yield

    def filter_by_liquidity(
        self,
        options: list[OptionContract],
        min_volume: int = 100,
        min_open_interest: int = 500,
    ) -> list[OptionContract]:
        """Filter options by liquidity thresholds.

        Args:
            options: List of options to filter
            min_volume: Minimum contract volume
            min_open_interest: Minimum open interest

        Returns:
            List of options that meet liquidity requirements
        """
        liquid = [
            opt
            for opt in options
            if opt.volume >= min_volume and opt.open_interest >= min_open_interest
        ]

        self._logger.debug(
            "filtered_by_liquidity",
            input_count=len(options),
            output_count=len(liquid),
            min_volume=min_volume,
            min_open_interest=min_open_interest,
        )

        return liquid

    def filter_by_dte(
        self,
        options: list[OptionContract],
        min_dte: int,
        max_dte: int,
        current_date: date | None = None,
    ) -> list[OptionContract]:
        """Filter options by days to expiration.

        Args:
            options: List of options to filter
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
            current_date: Current date (defaults to today)

        Returns:
            List of options within DTE range
        """
        if current_date is None:
            current_date = date.today()

        filtered = []
        for opt in options:
            dte = (opt.expiration - current_date).days
            if min_dte <= dte <= max_dte:
                filtered.append(opt)

        self._logger.debug(
            "filtered_by_dte",
            input_count=len(options),
            output_count=len(filtered),
            min_dte=min_dte,
            max_dte=max_dte,
        )

        return filtered

    def find_best_opportunity(
        self,
        option_chain: OptionChain,
        screening: OptionScreening,
        current_date: date | None = None,
    ) -> OptionRecommendation | None:
        """Find the best option opportunity from a chain.

        Finds the ATM put option with the highest annualized yield that
        meets liquidity and DTE requirements.

        Args:
            option_chain: Option chain to analyze
            screening: Option screening parameters
            current_date: Current date (defaults to today)

        Returns:
            OptionRecommendation if a suitable option is found, None otherwise
        """
        if current_date is None:
            current_date = date.today()

        stock_price = float(option_chain.underlying_price)
        if stock_price <= 0:
            self._logger.error("invalid_underlying_price", price=stock_price)
            return None

        # Find ATM puts
        atm_puts = self.find_atm_puts(option_chain, tolerance=screening.tolerance)

        if not atm_puts:
            self._logger.debug("no_atm_puts_found", symbol=option_chain.symbol)
            return None

        # Filter by DTE
        dte_filtered = self.filter_by_dte(
            atm_puts,
            screening.min_dte,
            screening.max_dte,
            current_date,
        )

        if not dte_filtered:
            self._logger.debug("no_puts_in_dte_range", symbol=option_chain.symbol)
            return None

        # Filter by liquidity
        liquid_puts = self.filter_by_liquidity(
            dte_filtered,
            screening.min_volume,
            screening.min_open_interest,
        )

        if not liquid_puts:
            self._logger.debug("no_liquid_puts", symbol=option_chain.symbol)
            return None

        # Find best yield
        best_put = None
        best_yield = 0.0

        for put in liquid_puts:
            try:
                yield_val = self.calculate_premium_yield(
                    put,
                    stock_price,
                    put.expiration,
                    current_date,
                )

                if yield_val >= screening.min_premium_yield and yield_val > best_yield:
                    best_yield = yield_val
                    best_put = put
            except Exception as e:
                self._logger.warning(
                    "yield_calculation_failed",
                    option=put.symbol,
                    error=str(e),
                )
                continue

        if best_put is None:
            self._logger.debug(
                "no_put_met_yield_threshold",
                symbol=option_chain.symbol,
                min_yield=screening.min_premium_yield,
            )
            return None

        dte = (best_put.expiration - current_date).days

        recommendation = OptionRecommendation(
            symbol=best_put.symbol,
            underlying_symbol=best_put.underlying_symbol,
            strike=float(best_put.strike),
            expiration=best_put.expiration,
            option_type=best_put.option_type,
            bid=float(best_put.bid),
            ask=float(best_put.ask),
            mid_price=float(best_put.mid_price),
            premium_yield=best_yield,
            volume=best_put.volume,
            open_interest=best_put.open_interest,
            implied_volatility=best_put.implied_volatility,
            delta=best_put.delta,
            reason=self._build_reason(best_put, best_yield, dte, stock_price),
        )

        self._logger.info(
            "best_opportunity_found",
            symbol=option_chain.symbol,
            option=recommendation.symbol,
            yield_val=best_yield,
            dte=dte,
        )

        return recommendation

    def analyze_all_expirations(
        self,
        option_chains: list[OptionChain],
        screening: OptionScreening,
        current_date: date | None = None,
    ) -> OptionRecommendation | None:
        """Analyze multiple option chains and find the best opportunity.

        Args:
            option_chains: List of option chains for different expirations
            screening: Option screening parameters
            current_date: Current date (defaults to today)

        Returns:
            Best OptionRecommendation across all chains, or None
        """
        best_rec = None
        best_yield = 0.0

        for chain in option_chains:
            rec = self.find_best_opportunity(chain, screening, current_date)
            if rec and rec.premium_yield > best_yield:
                best_yield = rec.premium_yield
                best_rec = rec

        if best_rec:
            self._logger.info(
                "best_opportunity_across_expirations",
                underlying=best_rec.underlying_symbol,
                option=best_rec.symbol,
                yield_val=best_yield,
            )

        return best_rec

    def _build_reason(
        self,
        put: OptionContract,
        yield_val: float,
        dte: int,
        stock_price: float,
    ) -> str:
        """Build a human-readable reason for the recommendation.

        Args:
            put: The recommended put option
            yield_val: Calculated annualized yield
            dte: Days to expiration
            stock_price: Current stock price

        Returns:
            Human-readable explanation string
        """
        strike_pct = (float(put.strike) / stock_price - 1) * 100
        direction = "below" if strike_pct < 0 else "above" if strike_pct > 0 else "at"

        return (
            f"${float(put.strike):.2f} strike ({abs(strike_pct):.1f}% {direction} spot), "
            f"{dte} days to expiration, "
            f"{yield_val:.1%} annualized yield, "
            f"${put.mid_price:.2f} mid price"
        )
