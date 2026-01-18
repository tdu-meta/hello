"""Strategy models for defining trading strategies.

This module provides dataclasses for defining trading strategies including
conditions, stock criteria, and option screening parameters.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Condition:
    """A single condition in a trading strategy.

    Conditions define the criteria that must be met for a strategy entry signal.
    Each condition has a type (e.g., "trend", "oversold", "bounce"), a rule
    expression, and optional parameters.

    Attributes:
        type: The condition type (trend, oversold, bounce, etc.)
        rule: The rule expression (e.g., "sma_20 > sma_60")
        parameters: Optional parameters for the condition (thresholds, lookbacks, etc.)
        description: Human-readable description of what this condition checks
        weight: Weight for calculating signal strength (default 1.0)
    """

    type: str
    rule: str
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    weight: float = 1.0


@dataclass(frozen=True)
class StockCriteria:
    """Criteria for filtering stocks before strategy evaluation.

    These criteria are applied to filter the universe of stocks down to
    those that meet basic fundamental or market cap requirements.

    Attributes:
        min_revenue: Minimum annual revenue in dollars
        min_market_cap: Minimum market capitalization in dollars
        max_market_cap: Maximum market capitalization in dollars (optional)
        min_price: Minimum stock price
        max_price: Maximum stock price (optional)
        exchanges: List of allowed exchanges (optional)
        sectors: List of allowed sectors (optional)
        exclude_sectors: List of sectors to exclude (optional)
    """

    min_revenue: int | None = None
    min_market_cap: int | None = None
    max_market_cap: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    exchanges: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    exclude_sectors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OptionScreening:
    """Parameters for screening option contracts.

    Defines how to select and filter options for the strategy.

    Attributes:
        min_premium_yield: Minimum annualized premium yield (as decimal, e.g., 0.02 for 2%)
        target_dte: Target days to expiration
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration
        tolerance: ATM strike tolerance as percentage (e.g., 0.05 for 5%)
        min_volume: Minimum option contract volume
        min_open_interest: Minimum option open interest
    """

    min_premium_yield: float = 0.02
    target_dte: int = 30
    min_dte: int = 7
    max_dte: int = 60
    tolerance: float = 0.05
    min_volume: int = 100
    min_open_interest: int = 500


@dataclass(frozen=True)
class Strategy:
    """A complete trading strategy definition.

    A strategy defines all aspects of a trading approach including which stocks
    to consider, what conditions must be met for entry, and how to select options.

    Attributes:
        name: Human-readable strategy name
        version: Strategy version string (semantic versioning recommended)
        description: Detailed description of the strategy
        stock_criteria: Criteria for filtering stocks
        entry_conditions: List of conditions that must all be met for entry
        option_screening: Parameters for option contract selection
        tags: Optional list of tags for categorization
    """

    name: str
    version: str
    description: str
    stock_criteria: StockCriteria
    entry_conditions: list[Condition]
    option_screening: OptionScreening
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate strategy definition after creation."""
        if not self.name:
            raise ValueError("Strategy name cannot be empty")
        if not self.version:
            raise ValueError("Strategy version cannot be empty")
        if not self.entry_conditions:
            raise ValueError("Strategy must have at least one entry condition")


@dataclass
class EvaluationResult:
    """Result of evaluating a symbol against a strategy.

    Attributes:
        symbol: The stock symbol that was evaluated
        strategy_name: Name of the strategy used for evaluation
        timestamp: When the evaluation was performed
        matches: Whether all entry conditions were met
        conditions_met: List of condition types that were met
        conditions_missed: List of condition types that were not met
        signal_strength: Calculated signal strength (0.0 to 1.0)
        details: Additional details about the evaluation
    """

    symbol: str
    strategy_name: str
    timestamp: Any
    matches: bool
    conditions_met: list[str]
    conditions_missed: list[str]
    signal_strength: float
    details: dict[str, Any] | None = None


@dataclass
class OptionRecommendation:
    """A recommended option contract for trading.

    Attributes:
        symbol: The option symbol (e.g., "AAPL240119P00150000")
        underlying_symbol: The underlying stock symbol
        strike: Strike price
        expiration: Expiration date
        option_type: "call" or "put"
        bid: Bid price
        ask: Ask price
        mid_price: Mid price between bid and ask
        premium_yield: Calculated annualized premium yield
        volume: Contract volume
        open_interest: Open interest
        implied_volatility: Implied volatility (if available)
        delta: Greek delta (if available)
        reason: Human-readable explanation for why this option was recommended
    """

    symbol: str
    underlying_symbol: str
    strike: float
    expiration: Any
    option_type: str
    bid: float
    ask: float
    mid_price: float
    premium_yield: float
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    delta: float | None = None
    reason: str = ""
