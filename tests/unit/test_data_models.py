"""Tests for data models."""

from datetime import date, datetime
from decimal import Decimal

from orion.data.models import (
    OHLCV,
    CompanyOverview,
    OptionChain,
    OptionContract,
    Quote,
    TechnicalIndicators,
)


class TestQuote:
    """Tests for Quote model."""

    def test_quote_creation(self) -> None:
        """Quote creates successfully with all fields."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            timestamp=datetime(2024, 1, 1, 10, 0),
            open=Decimal("148.00"),
            high=Decimal("151.00"),
            low=Decimal("147.50"),
            close=Decimal("150.00"),
            previous_close=Decimal("149.00"),
        )

        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.00")
        assert quote.volume == 1000000
        assert quote.previous_close == Decimal("149.00")

    def test_quote_calculates_change(self) -> None:
        """Quote calculates change from previous close."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            timestamp=datetime.now(),
            open=Decimal("148.00"),
            high=Decimal("151.00"),
            low=Decimal("147.50"),
            close=Decimal("150.00"),
            previous_close=Decimal("149.00"),
        )

        assert quote.change == Decimal("1.00")
        assert quote.change_percent is not None
        assert abs(quote.change_percent - 0.671) < 0.01

    def test_quote_without_previous_close(self) -> None:
        """Quote works without previous close."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            timestamp=datetime.now(),
            open=Decimal("148.00"),
            high=Decimal("151.00"),
            low=Decimal("147.50"),
            close=Decimal("150.00"),
        )

        assert quote.change is None
        assert quote.change_percent is None


class TestOptionContract:
    """Tests for OptionContract model."""

    def test_option_contract_creation(self) -> None:
        """OptionContract creates successfully."""
        contract = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=100,
            open_interest=500,
        )

        assert contract.symbol == "AAPL240119P00150000"
        assert contract.strike == Decimal("150.00")
        assert contract.option_type == "put"

    def test_mid_price_calculation(self) -> None:
        """Mid price calculates correctly."""
        contract = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.60"),
            last_price=Decimal("2.55"),
            volume=100,
            open_interest=500,
        )

        assert contract.mid_price == Decimal("2.55")

    def test_spread_calculation(self) -> None:
        """Bid-ask spread calculates correctly."""
        contract = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.60"),
            last_price=Decimal("2.55"),
            volume=100,
            open_interest=500,
        )

        assert contract.spread == Decimal("0.10")

    def test_is_liquid_check(self) -> None:
        """Liquidity check works correctly."""
        # Liquid option
        liquid = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=100,
            open_interest=500,
        )
        assert liquid.is_liquid is True

        # Illiquid option (low volume)
        illiquid = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=5,
            open_interest=500,
        )
        assert illiquid.is_liquid is False


class TestOptionChain:
    """Tests for OptionChain model."""

    def test_option_chain_creation(self) -> None:
        """OptionChain creates successfully."""
        chain = OptionChain(
            symbol="AAPL",
            expiration=date(2024, 1, 19),
            underlying_price=Decimal("150.00"),
        )

        assert chain.symbol == "AAPL"
        assert chain.expiration == date(2024, 1, 19)
        assert chain.underlying_price == Decimal("150.00")
        assert len(chain.calls) == 0
        assert len(chain.puts) == 0

    def test_get_atm_strike(self) -> None:
        """ATM strike calculation works correctly."""
        put_145 = OptionContract(
            symbol="AAPL240119P00145000",
            underlying_symbol="AAPL",
            strike=Decimal("145.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("1.50"),
            ask=Decimal("1.55"),
            last_price=Decimal("1.52"),
            volume=100,
            open_interest=500,
        )

        put_150 = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=100,
            open_interest=500,
        )

        chain = OptionChain(
            symbol="AAPL",
            expiration=date(2024, 1, 19),
            underlying_price=Decimal("149.00"),
            puts=[put_145, put_150],
        )

        # Should return 150 as it's closest to 149
        assert chain.get_atm_strike() == Decimal("150.00")

    def test_get_atm_put(self) -> None:
        """Get ATM put returns correct option."""
        put_150 = OptionContract(
            symbol="AAPL240119P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=date(2024, 1, 19),
            option_type="put",
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=100,
            open_interest=500,
        )

        chain = OptionChain(
            symbol="AAPL",
            expiration=date(2024, 1, 19),
            underlying_price=Decimal("150.00"),
            puts=[put_150],
        )

        atm_put = chain.get_atm_put()
        assert atm_put is not None
        assert atm_put.strike == Decimal("150.00")


class TestOHLCV:
    """Tests for OHLCV model."""

    def test_ohlcv_creation(self) -> None:
        """OHLCV creates successfully."""
        ohlcv = OHLCV(
            timestamp=datetime(2024, 1, 1),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("103.00"),
            volume=1000000,
        )

        assert ohlcv.open == Decimal("100.00")
        assert ohlcv.high == Decimal("105.00")
        assert ohlcv.low == Decimal("99.00")
        assert ohlcv.close == Decimal("103.00")

    def test_price_range_calculation(self) -> None:
        """Price range calculates correctly."""
        ohlcv = OHLCV(
            timestamp=datetime(2024, 1, 1),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("103.00"),
            volume=1000000,
        )

        assert ohlcv.price_range == Decimal("6.00")

    def test_body_size_calculation(self) -> None:
        """Candle body size calculates correctly."""
        # Bullish candle
        bullish = OHLCV(
            timestamp=datetime(2024, 1, 1),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("103.00"),
            volume=1000000,
        )
        assert bullish.body_size == Decimal("3.00")

        # Bearish candle
        bearish = OHLCV(
            timestamp=datetime(2024, 1, 1),
            open=Decimal("103.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("100.00"),
            volume=1000000,
        )
        assert bearish.body_size == Decimal("3.00")


class TestCompanyOverview:
    """Tests for CompanyOverview model."""

    def test_company_overview_creation(self) -> None:
        """CompanyOverview creates successfully."""
        overview = CompanyOverview(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            market_cap=3_000_000_000_000,
            revenue=400_000_000_000,
        )

        assert overview.symbol == "AAPL"
        assert overview.name == "Apple Inc."
        assert overview.market_cap == 3_000_000_000_000

    def test_meets_screener_criteria_pass(self) -> None:
        """Company passes screener criteria."""
        overview = CompanyOverview(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            market_cap=3_000_000_000_000,
            revenue=400_000_000_000,
        )

        # Should pass with lower thresholds
        assert overview.meets_screener_criteria(
            min_revenue=100_000_000_000, min_market_cap=1_000_000_000_000
        )

    def test_meets_screener_criteria_fail(self) -> None:
        """Company fails screener criteria."""
        overview = CompanyOverview(
            symbol="TINY",
            name="Tiny Corp",
            exchange="NASDAQ",
            market_cap=500_000_000,
            revenue=100_000_000,
        )

        # Should fail with higher thresholds
        assert not overview.meets_screener_criteria(
            min_revenue=1_000_000_000, min_market_cap=1_000_000_000
        )


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators model."""

    def test_technical_indicators_creation(self) -> None:
        """TechnicalIndicators creates successfully."""
        indicators = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            sma_20=150.0,
            sma_60=145.0,
            rsi_14=45.0,
        )

        assert indicators.symbol == "AAPL"
        assert indicators.sma_20 == 150.0
        assert indicators.rsi_14 == 45.0

    def test_is_oversold(self) -> None:
        """Oversold check works correctly."""
        oversold = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            rsi_14=25.0,
        )
        assert oversold.is_oversold() is True

        normal = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            rsi_14=50.0,
        )
        assert normal.is_oversold() is False

    def test_is_overbought(self) -> None:
        """Overbought check works correctly."""
        overbought = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            rsi_14=75.0,
        )
        assert overbought.is_overbought() is True

        normal = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            rsi_14=50.0,
        )
        assert normal.is_overbought() is False

    def test_is_bullish_trend(self) -> None:
        """Bullish trend check works correctly."""
        bullish = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            sma_20=150.0,
            sma_60=145.0,
        )
        assert bullish.is_bullish_trend() is True

        bearish = TechnicalIndicators(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            sma_20=140.0,
            sma_60=145.0,
        )
        assert bearish.is_bullish_trend() is False
