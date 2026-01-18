"""
Unit tests for OptionAnalyzer.

Tests for finding and analyzing ATM put options for the OFI strategy.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from orion.data.models import OptionChain, OptionContract
from orion.strategies.models import OptionScreening
from orion.strategies.option_analyzer import OptionAnalyzer


class TestOptionAnalyzer:
    """Test suite for OptionAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> OptionAnalyzer:
        """Create an OptionAnalyzer instance for testing."""
        return OptionAnalyzer()

    @pytest.fixture
    def sample_option_chain(self) -> OptionChain:
        """Create a sample option chain for testing."""
        underlying_price = Decimal("150.00")
        expiration = date.today() + timedelta(days=30)
        exp_str = expiration.strftime("%y%m%d")

        # Create a range of put options
        puts = [
            OptionContract(
                symbol=f"AAPL{exp_str}P{int(strike):06d}",
                underlying_symbol="AAPL",
                strike=Decimal(str(strike)),
                expiration=expiration,
                option_type="put",
                bid=Decimal("2.00"),
                ask=Decimal("2.20"),
                last_price=Decimal("2.10"),
                volume=500,
                open_interest=1000,
                implied_volatility=0.25,
            )
            for strike in [140.0, 145.0, 150.0, 155.0, 160.0]
        ]

        # Update the ATM put to have higher volume/OI
        puts[2].volume = 1000  # 150 strike
        puts[2].open_interest = 2000

        return OptionChain(
            symbol="AAPL",
            expiration=expiration,
            underlying_price=underlying_price,
            puts=puts,
            calls=[],
        )

    @pytest.fixture
    def liquid_option_chain(self) -> OptionChain:
        """Create an option chain with liquid and illiquid options."""
        underlying_price = Decimal("150.00")
        expiration = date.today() + timedelta(days=30)

        # ATM liquid put
        liquid_put = OptionContract(
            symbol="AAPL240130P00150000",
            underlying_symbol="AAPL",
            strike=Decimal("150.00"),
            expiration=expiration,
            option_type="put",
            bid=Decimal("3.00"),
            ask=Decimal("3.20"),
            last_price=Decimal("3.10"),
            volume=500,
            open_interest=1000,
            implied_volatility=0.30,
        )

        # OTM illiquid put
        illiquid_put = OptionContract(
            symbol="AAPL24030P00145000",
            underlying_symbol="AAPL",
            strike=Decimal("145.00"),
            expiration=expiration,
            option_type="put",
            bid=Decimal("1.00"),
            ask=Decimal("1.10"),
            last_price=Decimal("1.05"),
            volume=10,  # Low volume
            open_interest=50,  # Low OI
            implied_volatility=0.25,
        )

        return OptionChain(
            symbol="AAPL",
            expiration=expiration,
            underlying_price=underlying_price,
            puts=[liquid_put, illiquid_put],
            calls=[],
        )

    def test_find_atm_puts_default_tolerance(
        self, analyzer: OptionAnalyzer, sample_option_chain: OptionChain
    ) -> None:
        """Test finding ATM puts with default 5% tolerance."""
        atm_puts = analyzer.find_atm_puts(sample_option_chain)

        # With $150 underlying and 5% tolerance (142.50 - 157.50)
        # Strikes 145, 150, 155 should be included (140 and 160 are outside)
        assert len(atm_puts) == 3

        # Should be sorted by proximity to ATM (150 first)
        assert float(atm_puts[0].strike) == 150.0

    def test_find_atm_puts_custom_tolerance(
        self, analyzer: OptionAnalyzer, sample_option_chain: OptionChain
    ) -> None:
        """Test finding ATM puts with custom tolerance."""
        # 2% tolerance: 147 - 153
        atm_puts = analyzer.find_atm_puts(sample_option_chain, tolerance=0.02)

        # Only 150 should be in range (maybe 145 and 155 depending on exact calc)
        # 150 +/- 2% = 147-153, so only 150 is strictly in range
        assert len(atm_puts) >= 1
        assert float(atm_puts[0].strike) == 150.0

    def test_find_atm_puts_empty_chain(self, analyzer: OptionAnalyzer) -> None:
        """Test finding ATM puts with empty option chain."""
        empty_chain = OptionChain(
            symbol="TEST",
            expiration=date.today() + timedelta(days=30),
            underlying_price=Decimal("100.00"),
            puts=[],
            calls=[],
        )

        atm_puts = analyzer.find_atm_puts(empty_chain)
        assert len(atm_puts) == 0

    def test_calculate_premium_yield(self, analyzer: OptionAnalyzer) -> None:
        """Test premium yield calculation."""
        put = OptionContract(
            symbol="TEST",
            underlying_symbol="TEST",
            strike=Decimal("150.00"),
            expiration=date.today() + timedelta(days=30),
            option_type="put",
            bid=Decimal("3.00"),
            ask=Decimal("3.20"),
            last_price=Decimal("3.10"),
            volume=100,
            open_interest=500,
        )

        # $3.10 premium on $150 stock, 30 days to expiration
        # Daily yield = 3.10 / 150 = 0.02067
        # Annualized = 0.02067 * (365 / 30) = 0.2515
        yield_val = analyzer.calculate_premium_yield(
            put,
            150.0,
            date.today() + timedelta(days=30),
        )

        assert yield_val > 0.20  # Approximately 25%
        assert yield_val < 0.30

    def test_calculate_premium_yield_invalid_dte(self, analyzer: OptionAnalyzer) -> None:
        """Test premium yield with expired option."""
        put = OptionContract(
            symbol="TEST",
            underlying_symbol="TEST",
            strike=Decimal("150.00"),
            expiration=date.today() - timedelta(days=1),  # Expired
            option_type="put",
            bid=Decimal("3.00"),
            ask=Decimal("3.20"),
            last_price=Decimal("3.10"),
            volume=100,
            open_interest=500,
        )

        with pytest.raises(ValueError, match="days to expiration"):
            analyzer.calculate_premium_yield(put, 150.0, date.today())

    def test_filter_by_liquidity(
        self, analyzer: OptionAnalyzer, liquid_option_chain: OptionChain
    ) -> None:
        """Test filtering options by liquidity."""
        all_puts = liquid_option_chain.puts

        liquid = analyzer.filter_by_liquidity(
            all_puts,
            min_volume=100,
            min_open_interest=500,
        )

        # Only the liquid put should pass
        assert len(liquid) == 1
        assert liquid[0].strike == Decimal("150.00")

    def test_filter_by_liquidity_all_fail(self, analyzer: OptionAnalyzer) -> None:
        """Test filtering when all options are illiquid."""
        illiquid_puts = [
            OptionContract(
                symbol="TEST1",
                underlying_symbol="TEST",
                strike=Decimal("100.00"),
                expiration=date.today() + timedelta(days=30),
                option_type="put",
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last_price=Decimal("1.05"),
                volume=10,  # Below minimum
                open_interest=50,  # Below minimum
            )
        ]

        liquid = analyzer.filter_by_liquidity(illiquid_puts, min_volume=100, min_open_interest=500)
        assert len(liquid) == 0

    def test_filter_by_dte(self, analyzer: OptionAnalyzer) -> None:
        """Test filtering options by days to expiration."""
        base_date = date.today()

        options = [
            OptionContract(
                symbol="OPT1",
                underlying_symbol="TEST",
                strike=Decimal("100.00"),
                expiration=base_date + timedelta(days=5),  # Too soon
                option_type="put",
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last_price=Decimal("1.05"),
                volume=100,
                open_interest=500,
            ),
            OptionContract(
                symbol="OPT2",
                underlying_symbol="TEST",
                strike=Decimal("100.00"),
                expiration=base_date + timedelta(days=30),  # In range
                option_type="put",
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last_price=Decimal("1.05"),
                volume=100,
                open_interest=500,
            ),
            OptionContract(
                symbol="OPT3",
                underlying_symbol="TEST",
                strike=Decimal("100.00"),
                expiration=base_date + timedelta(days=90),  # Too far
                option_type="put",
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last_price=Decimal("1.05"),
                volume=100,
                open_interest=500,
            ),
        ]

        # Filter for 7-60 days
        filtered = analyzer.filter_by_dte(options, min_dte=7, max_dte=60, current_date=base_date)

        assert len(filtered) == 1
        assert filtered[0].expiration == base_date + timedelta(days=30)

    def test_find_best_opportunity_success(
        self, analyzer: OptionAnalyzer, liquid_option_chain: OptionChain
    ) -> None:
        """Test finding the best option opportunity."""
        screening = OptionScreening(
            min_premium_yield=0.01,  # Low threshold
            min_dte=7,
            max_dte=60,
            min_volume=100,
            min_open_interest=500,
        )

        recommendation = analyzer.find_best_opportunity(liquid_option_chain, screening)

        assert recommendation is not None
        assert recommendation.underlying_symbol == "AAPL"
        assert recommendation.strike == 150.0
        assert recommendation.premium_yield > 0

    def test_find_best_opportunity_no_liquid_puts(
        self, analyzer: OptionAnalyzer, sample_option_chain: OptionChain
    ) -> None:
        """Test finding best opportunity when no puts meet liquidity."""
        # Modify sample chain to have illiquid puts
        for put in sample_option_chain.puts:
            put.volume = 10
            put.open_interest = 50

        screening = OptionScreening(
            min_volume=100,
            min_open_interest=500,
        )

        recommendation = analyzer.find_best_opportunity(sample_option_chain, screening)

        assert recommendation is None

    def test_find_best_opportunity_no_puts_in_dte_range(
        self, analyzer: OptionAnalyzer, liquid_option_chain: OptionChain
    ) -> None:
        """Test finding best opportunity when no puts are in DTE range."""
        screening = OptionScreening(
            min_dte=60,  # Chain has 30 DTE
            max_dte=90,
        )

        recommendation = analyzer.find_best_opportunity(liquid_option_chain, screening)

        assert recommendation is None

    def test_find_best_opportunity_no_atm_puts(self, analyzer: OptionAnalyzer) -> None:
        """Test finding best opportunity when no ATM puts exist."""
        # Create chain with only far OTM puts
        far_otm_chain = OptionChain(
            symbol="AAPL",
            expiration=date.today() + timedelta(days=30),
            underlying_price=Decimal("150.00"),
            puts=[
                OptionContract(
                    symbol="AAPL_P100",
                    underlying_symbol="AAPL",
                    strike=Decimal("100.00"),  # Far OTM
                    expiration=date.today() + timedelta(days=30),
                    option_type="put",
                    bid=Decimal("0.50"),
                    ask=Decimal("0.60"),
                    last_price=Decimal("0.55"),
                    volume=100,
                    open_interest=500,
                )
            ],
            calls=[],
        )

        screening = OptionScreening(tolerance=0.05)  # 5% tolerance means 142.5-157.5

        recommendation = analyzer.find_best_opportunity(far_otm_chain, screening)

        # $100 strike is outside 5% tolerance of $150
        assert recommendation is None

    def test_analyze_all_expirations(self, analyzer: OptionAnalyzer) -> None:
        """Test analyzing multiple option chains."""
        screening = OptionScreening(
            min_premium_yield=0.01,
            min_dte=7,
            max_dte=60,
        )

        # Create multiple chains with different expirations
        chains = []
        for days in [15, 30, 45]:
            expiration = date.today() + timedelta(days=days)
            chain = OptionChain(
                symbol="AAPL",
                expiration=expiration,
                underlying_price=Decimal("150.00"),
                puts=[
                    OptionContract(
                        symbol=f"AAPL_P150_{days}",
                        underlying_symbol="AAPL",
                        strike=Decimal("150.00"),
                        expiration=expiration,
                        option_type="put",
                        bid=Decimal("2.00"),
                        ask=Decimal("2.20"),
                        last_price=Decimal("2.10"),
                        volume=200,
                        open_interest=600,
                    )
                ],
                calls=[],
            )
            chains.append(chain)

        best_rec = analyzer.analyze_all_expirations(chains, screening)

        assert best_rec is not None
        # Should find one of the chains
        assert best_rec.underlying_symbol == "AAPL"

    def test_recommendation_reason_formatting(
        self, analyzer: OptionAnalyzer, liquid_option_chain: OptionChain
    ) -> None:
        """Test that recommendation reason is formatted correctly."""
        screening = OptionScreening(min_premium_yield=0.01)

        recommendation = analyzer.find_best_opportunity(liquid_option_chain, screening)

        assert recommendation is not None
        assert recommendation.reason
        assert "strike" in recommendation.reason.lower()
        assert "days" in recommendation.reason.lower()
        assert "yield" in recommendation.reason.lower()
