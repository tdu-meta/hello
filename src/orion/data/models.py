"""Data models for market data and financial information."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal


@dataclass
class Quote:
    """Real-time quote for a stock symbol."""

    symbol: str
    price: Decimal
    volume: int
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_percent: float | None = None

    def __post_init__(self) -> None:
        """Calculate derived fields if not provided."""
        if self.previous_close and self.change is None:
            self.change = self.price - self.previous_close
        if self.previous_close and self.change_percent is None and self.previous_close != 0:
            self.change_percent = float(
                (self.price - self.previous_close) / self.previous_close * 100
            )


@dataclass
class OptionContract:
    """Individual option contract details."""

    symbol: str
    underlying_symbol: str
    strike: Decimal
    expiration: date
    option_type: Literal["call", "put"]
    bid: Decimal
    ask: Decimal
    last_price: Decimal
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price between bid and ask."""
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask - self.bid

    @property
    def is_liquid(self) -> bool:
        """Check if option has sufficient liquidity (basic heuristic)."""
        return self.volume >= 10 and self.open_interest >= 100


@dataclass
class OptionChain:
    """Complete option chain for a symbol at a given expiration."""

    symbol: str
    expiration: date
    underlying_price: Decimal
    calls: list[OptionContract] = field(default_factory=list)
    puts: list[OptionContract] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def get_atm_strike(self) -> Decimal:
        """Get the at-the-money strike price closest to underlying price."""
        all_strikes = sorted({c.strike for c in self.calls + self.puts})
        if not all_strikes:
            return self.underlying_price

        # Find closest strike to underlying price
        return min(all_strikes, key=lambda x: abs(x - self.underlying_price))

    def get_atm_put(self) -> OptionContract | None:
        """Get the ATM put option."""
        atm_strike = self.get_atm_strike()
        atm_puts = [p for p in self.puts if p.strike == atm_strike]
        return atm_puts[0] if atm_puts else None


@dataclass
class OHLCV:
    """OHLCV (candlestick) data point."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Decimal | None = None

    @property
    def price_range(self) -> Decimal:
        """Calculate price range for the period."""
        return self.high - self.low

    @property
    def body_size(self) -> Decimal:
        """Calculate candle body size."""
        return abs(self.close - self.open)


@dataclass
class CompanyOverview:
    """Company fundamental information."""

    symbol: str
    name: str
    exchange: str
    sector: str | None = None
    industry: str | None = None
    market_cap: int | None = None
    revenue: int | None = None
    revenue_per_share: Decimal | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    pe_ratio: float | None = None
    peg_ratio: float | None = None
    book_value: Decimal | None = None
    dividend_per_share: Decimal | None = None
    dividend_yield: float | None = None
    eps: Decimal | None = None
    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    beta: float | None = None
    week_52_high: Decimal | None = None
    week_52_low: Decimal | None = None
    moving_average_50: Decimal | None = None
    moving_average_200: Decimal | None = None
    shares_outstanding: int | None = None

    def meets_screener_criteria(
        self,
        min_revenue: int | None = None,
        min_market_cap: int | None = None,
    ) -> bool:
        """Check if company meets basic screening criteria."""
        if min_revenue and (not self.revenue or self.revenue < min_revenue):
            return False
        if min_market_cap and (not self.market_cap or self.market_cap < min_market_cap):
            return False
        return True


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators for a symbol."""

    symbol: str
    timestamp: datetime
    sma_20: float | None = None
    sma_50: float | None = None
    sma_60: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    volume_avg_20: float | None = None
    volume_avg_50: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    atr_14: float | None = None

    def is_oversold(self, threshold: float = 30.0) -> bool:
        """Check if RSI indicates oversold condition."""
        return self.rsi_14 is not None and self.rsi_14 < threshold

    def is_overbought(self, threshold: float = 70.0) -> bool:
        """Check if RSI indicates overbought condition."""
        return self.rsi_14 is not None and self.rsi_14 > threshold

    def is_bullish_trend(self) -> bool:
        """Check if showing bullish trend (20 SMA > 60 SMA)."""
        return self.sma_20 is not None and self.sma_60 is not None and self.sma_20 > self.sma_60
